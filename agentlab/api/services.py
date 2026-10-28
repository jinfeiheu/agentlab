"""API 服务构建:图、检索器、checkpointer/Store、线程修复与记忆 hooks。"""

import asyncio
import logging
from contextlib import AsyncExitStack
from dataclasses import dataclass

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from agentlab.agent.graph import build_graph
from agentlab.agent.memory import (
    detect_memory_candidate,
    maybe_extract_and_save,
    messages_used_save_memory,
    save_memory,
    search_memory,
)
from agentlab.config import (
    DATABASE_URL,
    DOCS_DIR,
    EMBED_DIMS,
    ENABLE_AUTO_MEMORY,
    LLM_RERANK_ENABLED,
    RAG_MODE,
    RERANK_DEVICE,
    RERANK_ENABLED,
    RERANK_MODEL,
    USE_DB,
    USE_MCP,
)
from agentlab.models import build_chat_model, build_embeddings
from agentlab.rag.loaders import build_inmemory_retriever
from agentlab.rag.retrieval import (
    build_pgvector_hybrid_retriever,
    build_reranker,
)
from agentlab.security.guard import redact_pii
from agentlab.tools.builtin import calculator, make_search_tool, send_report
from agentlab.tools.tickets import get_ticket

logger = logging.getLogger(__name__)


@dataclass
class Services:
    """应用依赖集合;测试可注入 fake graph。"""

    graph: object
    retriever: object = None
    db_check: object = None
    model: object = None
    memory_store: object = None
    _closer: object = None

    async def aclose(self) -> None:
        """释放 Postgres 连接等外部资源;内存模式无需处理。"""
        closer = self._closer
        self._closer = None
        if closer is not None:
            await closer()


def _needs_db_check() -> bool:
    """checkpointer/Store、混合检索或 MCP 知识库都依赖 Postgres。"""
    return USE_DB or RAG_MODE == "hybrid" or USE_MCP


async def _check_db() -> None:
    """执行 SELECT 1,供健康检查使用。"""
    from psycopg import AsyncConnection

    async with await AsyncConnection.connect(
        DATABASE_URL, connect_timeout=3
    ) as conn:
        await conn.execute("SELECT 1")


async def build_services() -> Services:
    """构建真实依赖;USE_DB=true 时改用 Postgres checkpointer 与 Store。"""
    retriever = None
    if USE_MCP:
        from agentlab.mcp.client import load_mcp_tools

        mcp_tools = await load_mcp_tools()
        missing = {"search_docs", "calculator"} - {
            tool.name for tool in mcp_tools
        }
        if missing:
            raise RuntimeError(f"MCP server 缺少工具:{sorted(missing)}")
        # 私有 ticket/记忆留在本地进程,只把公共检索/计算交给 MCP。
        tools = [
            *mcp_tools,
            get_ticket,
            save_memory,
            search_memory,
            send_report,
        ]
    else:
        retriever = (
            build_pgvector_hybrid_retriever()
            if RAG_MODE == "hybrid"
            else build_inmemory_retriever(DOCS_DIR)
        )
        reranker = build_reranker(
            use_model=RERANK_ENABLED,
            use_llm=LLM_RERANK_ENABLED,
            model_name=RERANK_MODEL,
            device=RERANK_DEVICE,
        )
        tools = [
            calculator,
            make_search_tool(retriever, reranker=reranker),
            get_ticket,
            save_memory,
            search_memory,
            send_report,
        ]
    model = build_chat_model(temperature=0)
    embeddings = build_embeddings()
    if not USE_DB:
        store = InMemoryStore(
            index={"dims": EMBED_DIMS, "embed": embeddings}
        )
        graph = build_graph(model, tools, InMemorySaver(), store=store)
        return Services(
            graph=graph,
            retriever=retriever,
            model=model,
            memory_store=store,
            db_check=_check_db if _needs_db_check() else None,
        )

    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from langgraph.store.base import TTLConfig
    from langgraph.store.postgres.aio import (
        AsyncPostgresStore,
        PostgresIndexConfig,
    )
    from psycopg.conninfo import make_conninfo

    # 启动时不要无限等待:连不上 Postgres 应在健康检查/启动错误里快速暴露。
    async_database_url = make_conninfo(DATABASE_URL, connect_timeout=3)
    stack = AsyncExitStack()
    try:
        saver = await stack.enter_async_context(
            AsyncPostgresSaver.from_conn_string(async_database_url)
        )
        store = await stack.enter_async_context(
            AsyncPostgresStore.from_conn_string(
                async_database_url,
                index=PostgresIndexConfig(
                    dims=EMBED_DIMS, embed=embeddings
                ),
                ttl=TTLConfig(
                    omit_expired=True, refresh_on_read=False
                ),
            )
        )
        await saver.setup()
        await store.setup()
        graph = build_graph(model, tools, saver, store=store)
    except Exception:
        await stack.aclose()
        raise
    return Services(
        graph=graph,
        retriever=retriever,
        db_check=_check_db,
        model=model,
        memory_store=store,
        _closer=stack.aclose,
    )


def _pending_tool_calls(messages) -> tuple[dict[str, str], bool]:
    """找出未闭合的工具调用;第二个返回值表示能否在消息尾部补 ToolMessage。"""
    pending: dict[str, str] = {}
    expected_ids: set[str] = set()
    last_pending_index = -1
    can_repair = True
    for index, message in enumerate(messages):
        if isinstance(message, AIMessage) or getattr(message, "type", None) == "ai":
            calls = getattr(message, "tool_calls", None) or []
            if calls:
                if pending:
                    can_repair = False
                pending = {
                    call.get("id"): call.get("name", "tool")
                    for call in calls
                    if call.get("id")
                }
                expected_ids = set(pending)
                last_pending_index = index
            elif pending:
                can_repair = False
        elif isinstance(message, ToolMessage) or getattr(
            message, "type", None
        ) == "tool":
            call_id = getattr(message, "tool_call_id", "") or ""
            if pending and call_id not in expected_ids:
                can_repair = False
            pending.pop(call_id, None)
        elif pending and index > last_pending_index:
            can_repair = False
    return pending, can_repair


async def _reset_thread(graph, thread_id: str) -> None:
    """删除线程的 checkpoint;用于无法安全修复的会话状态。"""
    checkpointer = getattr(graph, "checkpointer", None)
    if checkpointer is None:
        return
    adelete = getattr(checkpointer, "adelete_thread", None)
    if adelete is not None:
        await adelete(thread_id)
        return
    delete = getattr(checkpointer, "delete_thread", None)
    if delete is not None:
        delete(thread_id)


async def _prepare_thread(graph, config) -> None:
    """修复上一轮中断留下的悬空 tool_call,避免模型报 400。"""
    thread_id = config["configurable"]["thread_id"]
    aget_state = getattr(graph, "aget_state", None)
    if aget_state is None:
        return
    try:
        state = await aget_state(config)
    except Exception as exc:  # noqa: BLE001 - 状态读失败时宁可重置
        logger.warning(
            "读取会话 %s 状态失败,重置: %s", thread_id, redact_pii(str(exc))
        )
        await _reset_thread(graph, thread_id)
        return
    if state is None:
        return
    values = getattr(state, "values", None) or {}
    messages = values.get("messages", []) if isinstance(values, dict) else []
    interrupts = getattr(state, "interrupts", ()) or ()
    pending, can_repair = _pending_tool_calls(messages)
    if not pending and not interrupts and can_repair:
        return
    if interrupts or not can_repair:
        logger.warning(
            "会话 %s 状态不一致(interrupts=%s, pending=%s),重置",
            thread_id,
            bool(interrupts),
            list(pending),
        )
        await _reset_thread(graph, thread_id)
        return
    missing = [
        ToolMessage(
            content="上一次工具调用被中断，未返回结果。",
            name=name,
            tool_call_id=call_id,
            status="error",
        )
        for call_id, name in pending.items()
    ]
    aupdate_state = getattr(graph, "aupdate_state", None)
    if aupdate_state is None:
        await _reset_thread(graph, thread_id)
        return
    try:
        await aupdate_state(config, {"messages": missing}, as_node="tools")
        logger.warning("会话 %s 补齐了 %d 个中断的工具调用", thread_id, len(missing))
    except Exception as exc:  # noqa: BLE001 - 修复失败则重置
        logger.warning(
            "修复会话 %s 失败,重置: %s", thread_id, redact_pii(str(exc))
        )
        await _reset_thread(graph, thread_id)


async def _maybe_extract_memory(
    services, user, text: str, messages
) -> None:
    """规则命中且模型未显式 save_memory 时,做一次结构化抽取写入。"""
    if not ENABLE_AUTO_MEMORY or user is None or not text:
        return
    if not detect_memory_candidate(text):
        return
    if messages_used_save_memory(messages):
        return
    model = getattr(services, "model", None)
    store = getattr(services, "memory_store", None)
    if model is None or store is None:
        return
    try:
        await asyncio.to_thread(
            maybe_extract_and_save, model, store, user.user_id, text
        )
    except Exception as exc:  # noqa: BLE001 - 自动记忆失败不中断请求
        logger.warning("自动记忆失败: %s", redact_pii(str(exc)))


async def _post_turn_memory(
    graph, config, services, user, user_text: str
) -> None:
    """流式结束后从 checkpoint 取本轮消息,按需做结构化记忆抽取。"""
    if not ENABLE_AUTO_MEMORY or user is None or not user_text:
        return
    aget_state = getattr(graph, "aget_state", None)
    if aget_state is None:
        return
    try:
        state = await aget_state(config)
        values = getattr(state, "values", None) or {}
        messages = (
            values.get("messages", []) if isinstance(values, dict) else []
        )
        await _maybe_extract_memory(services, user, user_text, messages)
    except Exception as exc:  # noqa: BLE001 - 自动记忆失败不中断流
        logger.warning("自动记忆失败: %s", redact_pii(str(exc)))
