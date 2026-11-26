"""MCP server:本地纯工具(计算器、字数统计)。"""

import argparse

from mcp.server.fastmcp import FastMCP

from agentlab.rag_agent.tools.builtin import calculator as _calculator

mcp = FastMCP("agentlab-utils")


@mcp.tool()
def calculator(expression: str) -> str:
    """计算数学表达式,支持 + - * / // % ** 和括号。"""
    return _calculator.invoke({"expression": expression})


@mcp.tool()
def word_count(text: str) -> int:
    """统计文本字符数。"""
    return len(text)


def main() -> None:
    parser = argparse.ArgumentParser(description="AgentLab MCP utils server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8812)
    args = parser.parse_args()
    if args.transport == "streamable-http":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
