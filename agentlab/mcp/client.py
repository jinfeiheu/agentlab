"""MCP client:聚合知识库与工具两个 server。"""

import asyncio
import inspect
import sys

from langchain_mcp_adapters.client import MultiServerMCPClient

from agentlab.config import (
    PROJECT_ROOT,
    MCP_AGENTLAB_URL,
    MCP_TRANSPORT,
    MCP_UTILS_URL,
)

MCP_SERVER_CONFIG = {
    "agentlab": {
        "transport": "stdio",
        "command": sys.executable,
        "args": ["-m", "agentlab.mcp.knowledge_server"],
        "cwd": str(PROJECT_ROOT),
    },
    "utils": {
        "transport": "stdio",
        "command": sys.executable,
        "args": ["-m", "agentlab.mcp.utils_server"],
        "cwd": str(PROJECT_ROOT),
    },
}


def build_mcp_config() -> dict:
    """按 MCP_TRANSPORT 返回 stdio 或 streamable_http 配置。"""
    if MCP_TRANSPORT == "streamable_http":
        return {
            "agentlab": {
                "transport": "streamable_http",
                "url": MCP_AGENTLAB_URL,
            },
            "utils": {
                "transport": "streamable_http",
                "url": MCP_UTILS_URL,
            },
        }
    return MCP_SERVER_CONFIG


async def load_mcp_tools():
    """发现两个 server 的全部工具;兼容 get_tools 同步/异步版本。"""
    client = MultiServerMCPClient(build_mcp_config())
    tools = client.get_tools()
    if inspect.isawaitable(tools):
        tools = await tools
    return list(tools)


async def _demo() -> None:
    tools = await load_mcp_tools()
    print("工具:", sorted(tool.name for tool in tools))
    search = next((tool for tool in tools if tool.name == "search_docs"), None)
    if search is not None:
        result = await search.ainvoke({"query": "checkpointer 是什么"})
        print("\nsearch_docs:", result)
    calc = next((tool for tool in tools if tool.name == "calculator"), None)
    if calc is not None:
        result = await calc.ainvoke({"expression": "(12+8)*3"})
        print("\ncalculator:", result)


if __name__ == "__main__":
    asyncio.run(_demo())
