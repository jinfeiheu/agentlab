"""LangChain × LangGraph 学习示例:命令行入口。"""

import os
import sys
import uuid

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from config import DOCS_DIR
from graph import SYSTEM_PROMPT, build_graph, build_simple_graph
from models import build_chat_model
from rag import build_inmemory_retriever
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
    """构建检索器,把 Ollama 连接错误转成可读提示。"""
    try:
        return build_inmemory_retriever(DOCS_DIR)
    except Exception as exc:
        raise SystemExit(
            "语料索引构建失败,请确认 Ollama 已启动且已拉取 bge-m3。\n"
            f"原始错误:{exc}"
        ) from exc


def run_turn(graph, config, user_input: str) -> None:
    """执行一轮对话:流式打印 token、工具事件,必要时处理 HITL 确认。"""
    payload = {"messages": [("user", user_input)]}
    while True:
        print("助手 > ", end="", flush=True)
        for mode, data in graph.stream(
            payload, config=config, stream_mode=["messages", "updates"]
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
                for update in data.values():
                    if not isinstance(update, dict):
                        continue
                    for message in update.get("messages", []):
                        if isinstance(message, AIMessage) and message.tool_calls:
                            for call in message.tool_calls:
                                print(
                                    f"\n🔧 调用工具 {call['name']}({call['args']})",
                                    flush=True,
                                )
                        elif isinstance(message, ToolMessage):
                            content = (
                                message.content
                                if isinstance(message.content, str)
                                else str(message.content)
                            )
                            preview = (
                                content
                                if len(content) <= _TOOL_PREVIEW_CHARS
                                else content[:_TOOL_PREVIEW_CHARS] + " ...(已截断)"
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
    tools = [calculator, make_search_tool(retriever), send_report]
    checkpointer = InMemorySaver()
    model = build_chat_model(temperature=0)

    use_simple = "--simple" in sys.argv[1:]
    graph = (
        build_simple_graph(model, tools, checkpointer)
        if use_simple
        else build_graph(model, tools, checkpointer)
    )
    print(graph.get_graph().draw_mermaid())
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    mode_name = "create_agent 高层封装" if use_simple else "手写 StateGraph"
    print(f"🤖 LangChain × LangGraph 问答机器人(模式:{mode_name})")
    print("输入 /help 查看命令,直接输入问题开始对话。")

    while True:
        try:
            text = input("你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break
        if not text:
            continue
        if text in {"/quit", "/exit", "quit", "exit"}:
            print("再见。")
            break
        if text == "/help":
            print(HELP)
            continue
        if text == "/new":
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            print("已开启新会话,之前的对话记忆已清空。")
            continue
        try:
            run_turn(graph, config, text)
        except Exception as exc:
            print(f"\n调用失败:{exc}")


if __name__ == "__main__":
    main()
