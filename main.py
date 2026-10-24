"""LangChain × LangGraph 学习示例:命令行入口。"""

import os
import sys
import uuid

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    SystemMessage,
    ToolMessage,
)
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command

from auth import DEMO_USERS, UserContext
from context import compress_tool_content
from config import (
    DOCS_DIR,
    EMBED_DIMS,
    ENABLE_AUTO_MEMORY,
    LLM_RERANK_ENABLED,
    RAG_MODE,
    RERANK_DEVICE,
    RERANK_ENABLED,
    RERANK_MODEL,
)
from graph import SYSTEM_PROMPT, build_graph, build_simple_graph
from memory import (
    maybe_extract_and_save,
    messages_used_save_memory,
    save_memory,
    search_memory,
    summarize_and_save,
)
from models import build_chat_model, build_embeddings
from multi_agent import build_multi_agent_graph
from rag import build_inmemory_retriever
from retrieval import build_pgvector_hybrid_retriever, build_reranker
from security import check_input, redact_pii
from tickets import get_ticket
from tools import calculator, make_search_tool, send_report
from tracing import setup_tracing, shutdown_tracing

HELP = """命令:
  /new    开启新会话(清空多轮记忆)
  /help   查看帮助
  /quit   退出
其它输入直接与机器人对话。"""

_TOOL_PREVIEW_CHARS = 200


def ensure_prerequisites() -> None:
    """检查启动必需条件,缺失时给出中文提示。"""
    if not os.getenv("DEEPSEEK_API_KEY"):
        raise SystemExit(
            "缺少 DEEPSEEK_API_KEY:请复制 .env.example 为 .env 并填入你的 DeepSeek Key。"
        )
    if not DOCS_DIR.exists():
        raise SystemExit(f"找不到语料目录:{DOCS_DIR}")


def build_retriever_or_exit():
    """构建检索器,把 Ollama/Postgres 连接错误转成可读提示。"""
    try:
        if RAG_MODE == "hybrid":
            return build_pgvector_hybrid_retriever()
        return build_inmemory_retriever(DOCS_DIR)
    except Exception as exc:
        raise SystemExit(
            "语料索引构建失败,请确认 Ollama 已启动且已拉取 bge-m3。\n"
            "hybrid 模式还需要 Postgres 中已执行 ingest.py。\n"
            f"原始错误:{exc}"
        ) from exc


def guard_input(text: str) -> bool:
    """输入安全检查;拒绝时打印中文原因并返回 False。"""
    decision = check_input(text)
    if decision.allowed:
        return True
    print(decision.reason)
    return False


def cli_mode(argv: list[str]) -> str:
    """--multi 优先于 --simple;默认手写单 Agent 图。"""
    if "--multi" in argv:
        return "multi"
    if "--simple" in argv:
        return "simple"
    return "graph"


def resolve_cli_user(argv: list[str]) -> UserContext:
    """解析 --user,把 demo 用户名绑定成 UserContext;默认 alice。"""
    username = "alice"
    if "--user" in argv:
        index = argv.index("--user")
        if index + 1 >= len(argv):
            raise SystemExit("--user 需要一个用户名,例如 --user alice")
        username = argv[index + 1]
    user = DEMO_USERS.get(username)
    if user is None:
        raise SystemExit(
            f"未知用户:{username};可选:{', '.join(sorted(DEMO_USERS))}"
        )
    return UserContext(user_id=user.user_id)


def run_turn(
    graph,
    config,
    user_input: str,
    context=None,
    reset_scratchpad: bool = False,
    multi: bool = False,
) -> None:
    """执行一轮对话:单 Agent 流式 token,多 Agent 用 updates 展示路由。"""
    payload = {"messages": [("user", user_input)]}
    if reset_scratchpad:
        payload.update(
            {"research_notes": "", "draft": "", "review": "", "steps": 0}
        )
    stream_modes = ["updates"] if multi else ["messages", "updates"]
    while True:
        print("助手 > ", end="", flush=True)
        for mode, data in graph.stream(
            payload,
            config=config,
            context=context,
            stream_mode=stream_modes,
        ):
            if mode == "messages":
                chunk, _metadata = data
                if (
                    isinstance(chunk, (AIMessage, AIMessageChunk))
                    and isinstance(chunk.content, str)
                    and chunk.content
                ):
                    print(chunk.content, end="", flush=True)
            elif mode == "updates":
                if multi:
                    for node_name, update in (data or {}).items():
                        if not isinstance(update, dict):
                            continue
                        if node_name == "supervisor":
                            route = update.get("next")
                            if route:
                                print(
                                    f"\n🧭 supervisor -> {route}",
                                    flush=True,
                                )
                        elif node_name == "researcher":
                            print("\n🔎 researcher 完成", flush=True)
                        elif node_name == "writer":
                            print(
                                f"\n✍️ writer 草稿:\n{update.get('draft', '')}",
                                flush=True,
                            )
                        elif node_name == "critic":
                            print(
                                f"\n🧐 critic: "
                                f"{str(update.get('review', ''))[:120]}",
                                flush=True,
                            )
                    continue
                for update in data.values():
                    if not isinstance(update, dict):
                        continue
                    for message in update.get("messages", []):
                        if isinstance(message, AIMessage) and message.tool_calls:
                            for call in message.tool_calls:
                                print(
                                    "\n🔧 调用工具 "
                                    f"{call['name']}"
                                    f"({redact_pii(str(call['args']))})",
                                    flush=True,
                                )
                        elif isinstance(message, ToolMessage):
                            content = redact_pii(
                                message.content
                                if isinstance(message.content, str)
                                else str(message.content)
                            )
                            preview = compress_tool_content(
                                content, _TOOL_PREVIEW_CHARS
                            )
                            print(
                                f"\n📄 工具结果 [{message.name}]: {preview}",
                                flush=True,
                            )
        print()

        state = graph.get_state(config)
        if not state.interrupts:
            return

        value = state.interrupts[0].value
        if isinstance(value, dict):
            print(f"⚠️  {value.get('question', value)}")
            if "content" in value:
                print(f"   内容:{value['content']}")
        else:
            print(f"⚠️  {value}")
        answer = input("确认? (y/n) > ").strip()
        payload = Command(resume=answer)


def maybe_extract_turn(model, store, user, graph, config, text) -> None:
    """规则命中且本轮未显式 save_memory 时,做一次结构化抽取写入。"""
    if not ENABLE_AUTO_MEMORY:
        return
    try:
        state = graph.get_state(config)
        if getattr(state, "interrupts", ()):
            return
        values = getattr(state, "values", None) or {}
        messages = values.get("messages", []) if isinstance(values, dict) else []
        if messages_used_save_memory(messages):
            return
        maybe_extract_and_save(model, store, user.user_id, text)
    except Exception as exc:  # noqa: BLE001 - 自动记忆失败不影响对话
        print(f"自动记忆失败:{redact_pii(str(exc))}")


def finalize_session(model, store, user, graph, config) -> None:
    """会话结束时生成一条 episode,而不是每轮追加长期记忆。"""
    if not ENABLE_AUTO_MEMORY:
        return
    try:
        state = graph.get_state(config)
        if getattr(state, "interrupts", ()):
            return
        values = getattr(state, "values", None) or {}
        messages = values.get("messages", []) if isinstance(values, dict) else []
        summary = values.get("summary", "") if isinstance(values, dict) else ""
        if summary:
            messages = [
                SystemMessage(content=f"较早对话摘要:\n{summary}"),
                *messages,
            ]
        if messages:
            thread_id = (config.get("configurable") or {}).get(
                "thread_id", ""
            )
            summarize_and_save(
                model, store, user.user_id, messages, thread_id=thread_id
            )
    except Exception as exc:  # noqa: BLE001 - 自动记忆失败不影响退出
        print(f"自动记忆失败:{redact_pii(str(exc))}")


def main() -> None:
    """启动终端问答机器人:初始化追踪,并保证退出时刷出 span。"""
    ensure_prerequisites()
    setup_tracing()
    try:
        _run_cli()
    finally:
        shutdown_tracing()


def _run_cli() -> None:
    """构建检索器与图,进入终端交互循环。"""
    print("正在构建知识库索引(首次会加载 bge-m3)...")
    retriever = build_retriever_or_exit()
    user = resolve_cli_user(sys.argv[1:])
    store = InMemoryStore(
        index={"dims": EMBED_DIMS, "embed": build_embeddings()}
    )
    checkpointer = InMemorySaver()
    model = build_chat_model(temperature=0)
    mode = cli_mode(sys.argv[1:])

    if mode == "multi":
        graph = build_multi_agent_graph(
            model, retriever, checkpointer, store=store
        )
        mode_name = "Supervisor 多 Agent"
    else:
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
        graph = (
            build_simple_graph(model, tools, checkpointer, store=store)
            if mode == "simple"
            else build_graph(model, tools, checkpointer, store=store)
        )
        mode_name = (
            "create_agent 高层封装"
            if mode == "simple"
            else "手写 StateGraph"
        )

    print(graph.get_graph().draw_mermaid())
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    print(
        f"🤖 LangChain × LangGraph 问答机器人"
        f"(模式:{mode_name},用户:{user.user_id})"
    )
    print("输入 /help 查看命令,直接输入问题开始对话。")

    while True:
        try:
            text = input("你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            finalize_session(model, store, user, graph, config)
            print("\n再见。")
            break
        if not text:
            continue
        if text in {"/quit", "/exit", "quit", "exit"}:
            finalize_session(model, store, user, graph, config)
            print("再见。")
            break
        if text == "/help":
            print(HELP)
            continue
        if text == "/new":
            finalize_session(model, store, user, graph, config)
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            print("已开启新会话,之前的对话记忆已清空。")
            continue
        if not guard_input(text):
            continue
        try:
            run_turn(
                graph,
                config,
                text,
                context=user,
                reset_scratchpad=mode == "multi",
                multi=mode == "multi",
            )
            maybe_extract_turn(model, store, user, graph, config, text)
        except Exception as exc:
            print(f"\n调用失败:{redact_pii(str(exc))}")


if __name__ == "__main__":
    main()
