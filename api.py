"""FastAPI 服务:JWT 登录、对话、SSE 流式输出与最小网页。"""

import asyncio
import inspect
import json
import logging
import re
import time
from contextlib import AsyncExitStack, aclosing, asynccontextmanager
from dataclasses import dataclass, field

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command
from pydantic import BaseModel

from auth import UserContext, login as authenticate, verify_token
from config import (
    BASE_DIR,
    DATABASE_URL,
    DOCS_DIR,
    EMBED_DIMS,
    ENABLE_AUTO_MEMORY,
    RAG_MODE,
    RATE_LIMIT_PER_MINUTE,
    RERANK_DEVICE,
    RERANK_ENABLED,
    RERANK_MODEL,
    LLM_RERANK_ENABLED,
    REQUEST_TIMEOUT,
    USE_DB,
    USE_MCP,
)
from context import compress_tool_content
from graph import build_graph
from memory import (
    detect_memory_candidate,
    maybe_extract_and_save,
    messages_used_save_memory,
    save_memory,
    search_memory,
)
from models import build_chat_model, build_embeddings
from rag import build_inmemory_retriever
from retrieval import build_pgvector_hybrid_retriever, build_reranker
from security import StreamingRedactor, check_input, redact_pii
from tickets import get_ticket
from tools import calculator, make_search_tool, send_report
from tracing import setup_tracing, shutdown_tracing

STATIC_DIR = BASE_DIR / "static"
_SOURCE_RE = re.compile(r"\[来源:([^\]]+)\]")
_TOOL_RESULT_CHARS = 500

logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    """登录请求。"""

    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应。"""

    token: str


class ChatRequest(BaseModel):
    """一轮对话请求。"""

    message: str
    session_id: str


class ResumeRequest(BaseModel):
    """恢复一次被 interrupt 暂停的工具调用。"""

    session_id: str
    answer: str


class ChatResponse(BaseModel):
    """非流式对话响应;interrupt 非空表示等待人工确认。"""

    answer: str
    sources: list[str]
    interrupt: dict | None = None


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


@dataclass
class RateLimiter:
    """按 user_id 的滑动窗口限流。"""

    limit: int
    window_seconds: float = 60.0
    hits: dict[str, list[float]] = field(default_factory=dict)

    def allow(self, user_id: str) -> bool:
        """记录一次请求;超过窗口上限返回 False。"""
        now = time.monotonic()
        recent = [
            stamp
            for stamp in self.hits.get(user_id, [])
            if now - stamp < self.window_seconds
        ]
        if len(recent) >= self.limit:
            self.hits[user_id] = recent
            return False
        recent.append(now)
        self.hits[user_id] = recent
        return True


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
        from mcp_client import load_mcp_tools

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
        graph = build_graph(
            model, tools, InMemorySaver(), store=store
        )
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


def sse(payload: dict) -> str:
    """把一个事件编码成 SSE data 帧。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _refusal_events(message: str):
    """把输入拒绝包装成与正常流一致的 token + done 事件。"""

    async def events():
        yield sse({"type": "token", "text": message})
        yield sse({"type": "done", "sources": []})

    return events()


def _content_text(content) -> str:
    """把 str 或内容块列表统一成字符串。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "".join(parts)
    return ""


def _message_text(message) -> str:
    content = (
        message.get("content")
        if isinstance(message, dict)
        else getattr(message, "content", None)
    )
    return _content_text(content)


def _extract_answer(result) -> str:
    """取最后一条有内容的 AI 消息。"""
    messages = result.get("messages", []) if isinstance(result, dict) else []
    for message in reversed(messages):
        role = (
            message.get("type")
            if isinstance(message, dict)
            else getattr(message, "type", None)
        )
        if role not in ("ai", "assistant"):
            continue
        text = _message_text(message)
        if text.strip():
            return redact_pii(text)
    return ""


def _sources_from_text(text: str) -> list[str]:
    """提取 [来源:...] 标记。"""
    return [item.strip() for item in _SOURCE_RE.findall(text) if item.strip()]


def _dedupe(items) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _extract_sources(result) -> list[str]:
    """从 ToolMessage 和回答中收集来源。"""
    messages = result.get("messages", []) if isinstance(result, dict) else []
    return _dedupe(
        redact_pii(source)
        for message in messages
        for source in _sources_from_text(_message_text(message))
    )


def _interrupt_payload(state) -> dict | None:
    """把 LangGraph 的 interrupt 状态整理成前端可用的事件。"""
    interrupts = getattr(state, "interrupts", ()) or ()
    if not interrupts:
        return None
    value = getattr(interrupts[0], "value", None)
    if isinstance(value, dict):
        return {
            "question": redact_pii(str(value.get("question", ""))),
            "content": redact_pii(str(value.get("content", ""))),
        }
    return {"question": redact_pii(str(value or "")), "content": ""}


async def _has_interrupt(graph, config) -> bool:
    """线程是否有 pending interrupt;fake graph 没有 aget_state 时视为没有。"""
    aget_state = getattr(graph, "aget_state", None)
    if aget_state is None:
        return False
    state = await aget_state(config)
    return bool(getattr(state, "interrupts", ()))


async def _get_interrupt(graph, config) -> dict | None:
    """读取线程当前的 pending interrupt;fake graph 没有 aget_state 时返回 None。"""
    aget_state = getattr(graph, "aget_state", None)
    if aget_state is None:
        return None
    try:
        state = await aget_state(config)
    except Exception as exc:  # noqa: BLE001 - 读状态失败不影响已有回答
        logger.warning("读取 interrupt 状态失败: %s", redact_pii(str(exc)))
        return None
    return _interrupt_payload(state)


def _redact_value(value):
    """递归脱敏工具参数/结果里的字符串,前端展示不出现原始 PII。"""
    if isinstance(value, str):
        return redact_pii(value)
    if isinstance(value, dict):
        return {key: _redact_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_value(item) for item in value]
    return value


def _tool_events(message) -> list[dict]:
    """把一条消息转换成 tool_call / tool_result 事件。"""
    events: list[dict] = []
    for call in getattr(message, "tool_calls", None) or []:
        events.append(
            {
                "type": "tool_call",
                "id": call.get("id") or "",
                "name": call.get("name", ""),
                "args": _redact_value(call.get("args", {})),
            }
        )
    if isinstance(message, ToolMessage) or getattr(message, "type", None) == "tool":
        events.append(
            {
                "type": "tool_result",
                "tool_call_id": getattr(message, "tool_call_id", "") or "",
                "name": getattr(message, "name", ""),
                "content": compress_tool_content(
                    redact_pii(_message_text(message)), _TOOL_RESULT_CHARS
                ),
            }
        )
    return events


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


async def _chat_events(
    graph,
    payload,
    config,
    request,
    timeout,
    lock,
    context=None,
    services=None,
    user_text: str = "",
    skip_prepare: bool = False,
):
    """把 graph 流转换成 SSE 事件;负责串行、修复、超时、断连和异常上报。"""
    sources: list[str] = []
    answer_parts: list[str] = []
    redactor = StreamingRedactor()
    try:
        async with lock:
            deadline = time.monotonic() + timeout
            if skip_prepare:
                remaining = max(0.01, deadline - time.monotonic())
                try:
                    has_interrupt = await asyncio.wait_for(
                        _has_interrupt(graph, config), timeout=remaining
                    )
                except asyncio.TimeoutError:
                    yield sse(
                        {"type": "error", "message": "request timeout"}
                    )
                    return
                if not has_interrupt:
                    yield sse(
                        {"type": "error", "message": "no pending interrupt"}
                    )
                    return
            else:
                remaining = max(0.01, deadline - time.monotonic())
                try:
                    await asyncio.wait_for(
                        _prepare_thread(graph, config), timeout=remaining
                    )
                except asyncio.TimeoutError:
                    yield sse(
                        {"type": "error", "message": "request timeout"}
                    )
                    return

            async with aclosing(
                graph.astream(
                    payload,
                    config=config,
                    context=context,
                    stream_mode=["messages", "updates"],
                )
            ) as stream:
                iterator = stream.__aiter__()
                while True:
                    if await request.is_disconnected():
                        return
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        yield sse(
                            {"type": "error", "message": "request timeout"}
                        )
                        return
                    try:
                        mode, data = await asyncio.wait_for(
                            iterator.__anext__(), timeout=remaining
                        )
                    except StopAsyncIteration:
                        break
                    except asyncio.TimeoutError:
                        yield sse(
                            {"type": "error", "message": "request timeout"}
                        )
                        return
                    if mode == "messages":
                        chunk, _metadata = data
                        if not isinstance(chunk, (AIMessage, AIMessageChunk)):
                            continue
                        text = _message_text(chunk)
                        if text:
                            answer_parts.append(text)
                            safe = redactor.feed(text)
                            if safe:
                                yield sse({"type": "token", "text": safe})
                    elif mode == "updates":
                        for update in (data or {}).values():
                            if not isinstance(update, dict):
                                continue
                            for message in update.get("messages", []):
                                if isinstance(message, ToolMessage) or getattr(
                                    message, "type", None
                                ) == "tool":
                                    sources.extend(
                                        _sources_from_text(_message_text(message))
                                    )
                                for event in _tool_events(message):
                                    yield sse(event)
            tail = redactor.flush()
            if tail:
                yield sse({"type": "token", "text": tail})
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                yield sse({"type": "error", "message": "request timeout"})
                return
            try:
                interrupt = await asyncio.wait_for(
                    _get_interrupt(graph, config), timeout=remaining
                )
            except asyncio.TimeoutError:
                yield sse({"type": "error", "message": "request timeout"})
                return
            if interrupt:
                yield sse({"type": "interrupt", **interrupt})
            elif services is not None and user_text:
                remaining = deadline - time.monotonic()
                if remaining > 0:
                    try:
                        await asyncio.wait_for(
                            _post_turn_memory(
                                graph,
                                config,
                                services,
                                context,
                                user_text,
                            ),
                            timeout=remaining,
                        )
                    except asyncio.TimeoutError:
                        logger.warning(
                            "流式轮次结束后记忆抽取超时,已跳过"
                        )
            yield sse(
                {
                    "type": "done",
                    "sources": _dedupe(
                        redact_pii(source)
                        for source in (
                            sources
                            + _sources_from_text("".join(answer_parts))
                        )
                    ),
                }
            )
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - 生成器内错误统一发 error 事件
        yield sse({"type": "error", "message": redact_pii(str(exc))})


def get_current_user(
    authorization: str | None = Header(default=None),
) -> UserContext:
    """从 Bearer token 解析用户身份;失败统一 401。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization[len("Bearer ") :].strip()
    try:
        user_id = verify_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc
    return UserContext(user_id=user_id)


def get_services(request: Request) -> Services:
    """从 app.state 取服务集合;启动失败时统一 503。"""
    services = request.app.state.services
    if services is None:
        raise HTTPException(
            status_code=503,
            detail=getattr(request.app.state, "startup_error", "服务未就绪"),
        )
    return services


def get_thread_lock(app: FastAPI, thread_id: str) -> asyncio.Lock:
    """同一 thread 的请求串行执行,避免 checkpoint 状态交错。"""
    locks = app.state.thread_locks
    lock = locks.get(thread_id)
    if lock is None:
        lock = asyncio.Lock()
        locks[thread_id] = lock
    return lock


def create_app(services: Services | None = None) -> FastAPI:
    """创建 FastAPI 应用;传入 services 时跳过真实依赖构建。"""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        tracing_started = False
        try:
            if app.state.services is None:
                setup_tracing()
                tracing_started = True
                try:
                    app.state.services = await build_services()
                except Exception as exc:  # noqa: BLE001 - 启动失败降级为 503
                    logger.error("服务初始化失败: %s", redact_pii(str(exc)))
                    app.state.startup_error = (
                        f"服务初始化失败: {redact_pii(str(exc))}"
                    )
            yield
        finally:
            current = app.state.services
            aclose = getattr(current, "aclose", None)
            if aclose is not None:
                await aclose()
            if tracing_started:
                shutdown_tracing()

    app = FastAPI(title="Agent Interview Lab", lifespan=lifespan)
    app.state.services = services
    app.state.startup_error = None
    app.state.limiter = RateLimiter(RATE_LIMIT_PER_MINUTE)
    app.state.thread_locks: dict[str, asyncio.Lock] = {}

    @app.post("/login", response_model=LoginResponse)
    def login_endpoint(body: LoginRequest) -> LoginResponse:
        token = authenticate(body.username, body.password)
        if token is None:
            raise HTTPException(
                status_code=401, detail="invalid username or password"
            )
        return LoginResponse(token=token)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        services = app.state.services
        if services is None:
            raise HTTPException(
                status_code=503,
                detail=getattr(app.state, "startup_error", "服务未就绪"),
            )
        check = getattr(services, "db_check", None)
        if check is not None:
            try:
                result = check()
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:  # noqa: BLE001 - 健康检查失败统一 503
                logger.warning(
                    "数据库健康检查失败: %s", redact_pii(str(exc))
                )
                raise HTTPException(
                    status_code=503, detail="数据库不可用"
                ) from exc
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.post("/chat", response_model=ChatResponse)
    async def chat(
        body: ChatRequest,
        user: UserContext = Depends(get_current_user),
        svc: Services = Depends(get_services),
    ) -> ChatResponse:
        if not app.state.limiter.allow(user.user_id):
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        decision = check_input(body.message)
        if not decision.allowed:
            return ChatResponse(answer=decision.reason, sources=[])
        thread_id = f"{user.user_id}:{body.session_id}"
        config = {"configurable": {"thread_id": thread_id}}
        async with get_thread_lock(app, thread_id):
            try:
                await asyncio.wait_for(
                    _prepare_thread(svc.graph, config),
                    timeout=REQUEST_TIMEOUT,
                )
            except asyncio.TimeoutError as exc:
                raise HTTPException(
                    status_code=504, detail="request timeout"
                ) from exc
            try:
                result = await asyncio.wait_for(
                    svc.graph.ainvoke(
                        {"messages": [("user", body.message)]},
                        config=config,
                        context=user,
                    ),
                    timeout=REQUEST_TIMEOUT,
                )
            except asyncio.TimeoutError as exc:
                raise HTTPException(
                    status_code=504, detail="request timeout"
                ) from exc
            except Exception as exc:  # noqa: BLE001 - 统一成 500,避免泄漏堆栈
                raise HTTPException(
                    status_code=500, detail="chat failed"
                ) from exc
            interrupt = await _get_interrupt(svc.graph, config)
        if interrupt is None:
            try:
                await asyncio.wait_for(
                    _maybe_extract_memory(
                        svc, user, body.message, result.get("messages", [])
                    ),
                    timeout=min(REQUEST_TIMEOUT, 10),
                )
            except asyncio.TimeoutError:
                logger.warning("非流式轮次结束后记忆抽取超时,已跳过")
        return ChatResponse(
            answer=_extract_answer(result),
            sources=_extract_sources(result),
            interrupt=interrupt,
        )

    @app.post("/chat/resume", response_model=ChatResponse)
    async def chat_resume(
        body: ResumeRequest,
        user: UserContext = Depends(get_current_user),
        svc: Services = Depends(get_services),
    ) -> ChatResponse:
        """恢复 pending interrupt;没有中断时返回 409。"""
        if not app.state.limiter.allow(user.user_id):
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        thread_id = f"{user.user_id}:{body.session_id}"
        config = {"configurable": {"thread_id": thread_id}}
        async with get_thread_lock(app, thread_id):
            aget_state = getattr(svc.graph, "aget_state", None)
            if aget_state is None:
                raise HTTPException(
                    status_code=409, detail="no pending interrupt"
                )
            try:
                state = await asyncio.wait_for(
                    aget_state(config), timeout=REQUEST_TIMEOUT
                )
            except asyncio.TimeoutError as exc:
                raise HTTPException(
                    status_code=504, detail="request timeout"
                ) from exc
            if not getattr(state, "interrupts", ()):
                raise HTTPException(
                    status_code=409, detail="no pending interrupt"
                )
            try:
                result = await asyncio.wait_for(
                    svc.graph.ainvoke(
                        Command(resume=body.answer),
                        config=config,
                        context=user,
                    ),
                    timeout=REQUEST_TIMEOUT,
                )
            except asyncio.TimeoutError as exc:
                raise HTTPException(
                    status_code=504, detail="request timeout"
                ) from exc
            except Exception as exc:  # noqa: BLE001 - 统一成 500
                raise HTTPException(
                    status_code=500, detail="resume failed"
                ) from exc
            interrupt = await _get_interrupt(svc.graph, config)
        return ChatResponse(
            answer=_extract_answer(result),
            sources=_extract_sources(result),
            interrupt=interrupt,
        )

    @app.post("/chat/stream/resume")
    async def chat_stream_resume(
        body: ResumeRequest,
        request: Request,
        user: UserContext = Depends(get_current_user),
        svc: Services = Depends(get_services),
    ) -> StreamingResponse:
        """流式恢复 pending interrupt;没有中断时返回 409。"""
        if not app.state.limiter.allow(user.user_id):
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        thread_id = f"{user.user_id}:{body.session_id}"
        config = {"configurable": {"thread_id": thread_id}}
        try:
            has_interrupt = await asyncio.wait_for(
                _has_interrupt(svc.graph, config), timeout=REQUEST_TIMEOUT
            )
        except asyncio.TimeoutError as exc:
            raise HTTPException(
                status_code=504, detail="request timeout"
            ) from exc
        if not has_interrupt:
            raise HTTPException(status_code=409, detail="no pending interrupt")
        return StreamingResponse(
            _chat_events(
                svc.graph,
                Command(resume=body.answer),
                config,
                request,
                REQUEST_TIMEOUT,
                get_thread_lock(app, thread_id),
                context=user,
                services=svc,
                skip_prepare=True,
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/chat/stream")
    async def chat_stream(
        body: ChatRequest,
        request: Request,
        user: UserContext = Depends(get_current_user),
        svc: Services = Depends(get_services),
    ) -> StreamingResponse:
        if not app.state.limiter.allow(user.user_id):
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        decision = check_input(body.message)
        if not decision.allowed:
            return StreamingResponse(
                _refusal_events(decision.reason),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )
        thread_id = f"{user.user_id}:{body.session_id}"
        config = {"configurable": {"thread_id": thread_id}}
        return StreamingResponse(
            _chat_events(
                svc.graph,
                {"messages": [("user", body.message)]},
                config,
                request,
                REQUEST_TIMEOUT,
                get_thread_lock(app, thread_id),
                context=user,
                services=svc,
                user_text=body.message,
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


app = create_app()
