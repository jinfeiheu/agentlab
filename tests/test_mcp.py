"""MCP server/client 测试:stdio 配置与真实工具发现。"""

import os

import pytest

from mcp_client import MCP_SERVER_CONFIG, load_mcp_tools

integration = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="需要真实 MCP 子进程、Ollama 与 Postgres;设置 RUN_INTEGRATION=1 后运行",
)


def test_mcp_server_config_uses_stdio():
    config = MCP_SERVER_CONFIG["agentlab"]
    assert config["transport"] == "stdio"
    assert config["command"]
    assert "mcp_server.py" in " ".join(config["args"])
    assert config["cwd"]


@pytest.mark.integration
@integration
async def test_mcp_client_loads_search_docs():
    tools = await load_mcp_tools()
    names = [tool.name for tool in tools]
    assert "search_docs" in names
    tool = next(tool for tool in tools if tool.name == "search_docs")
    result = await tool.ainvoke({"query": "checkpointer"})
    assert "checkpointer" in str(result).lower()
