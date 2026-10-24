"""MCP client:通过 stdio 启动 agentlab server,发现并调用工具。"""

import asyncio
import inspect

from langchain_mcp_adapters.client import MultiServerMCPClient

from config import BASE_DIR

MCP_SERVER_CONFIG = {
    "agentlab": {
        "transport": "stdio",
        "command": "uv",
        "args": ["run", "python", "mcp_server.py"],
        "cwd": str(BASE_DIR),
    }
}


async def load_mcp_tools():
    """发现 MCP server 暴露的工具;兼容 get_tools 同步/异步两种版本。"""
    client = MultiServerMCPClient(MCP_SERVER_CONFIG)
    tools = client.get_tools()
    if inspect.isawaitable(tools):
        tools = await tools
    return list(tools)


async def _demo() -> None:
    tools = await load_mcp_tools()
    print("工具:", [tool.name for tool in tools])
    tool = next(tool for tool in tools if tool.name == "search_docs")
    result = await tool.ainvoke({"query": "checkpointer 是什么"})
    print(result)


if __name__ == "__main__":
    asyncio.run(_demo())
