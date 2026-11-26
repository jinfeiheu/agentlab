"""MCP server/client 测试:stdio 配置与真实工具发现。"""

import os

import pytest

from agentlab.rag_agent.mcp.client import MCP_SERVER_CONFIG, load_mcp_tools

integration = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="需要真实 MCP 子进程、Ollama 与 Postgres;设置 RUN_INTEGRATION=1 后运行",
)


def test_mcp_server_config_uses_stdio():
    assert set(MCP_SERVER_CONFIG) == {"agentlab", "utils"}
    for config in MCP_SERVER_CONFIG.values():
        assert config["transport"] == "stdio"
        assert config["command"]
        assert config["cwd"]
    assert "agentlab.rag_agent.mcp.knowledge_server" in " ".join(
        MCP_SERVER_CONFIG["agentlab"]["args"]
    )
    assert "agentlab.rag_agent.mcp.utils_server" in " ".join(
        MCP_SERVER_CONFIG["utils"]["args"]
    )


@pytest.mark.integration
@integration
async def test_mcp_client_loads_search_docs():
    tools = await load_mcp_tools()
    names = {tool.name for tool in tools}
    assert {
        "search_docs",
        "list_sources",
        "doc_stats",
        "calculator",
        "word_count",
    } <= names

    search = next(tool for tool in tools if tool.name == "search_docs")
    result = await search.ainvoke({"query": "checkpointer"})
    assert "checkpointer" in str(result).lower()

    calc = next(tool for tool in tools if tool.name == "calculator")
    result = await calc.ainvoke({"expression": "(12+8)*3"})
    assert "60" in str(result)

    sources_tool = next(tool for tool in tools if tool.name == "list_sources")
    sources = await sources_tool.ainvoke({})
    assert "02-langgraph.md#" in str(sources)
