"""MCP 多 server 与 transport 配置测试。"""

import agentlab.rag_agent.mcp.client as mcp_client


def test_build_mcp_config_stdio(monkeypatch):
    monkeypatch.setattr(mcp_client, "MCP_TRANSPORT", "stdio")
    config = mcp_client.build_mcp_config()
    assert set(config) == {"agentlab", "utils"}
    assert config["agentlab"]["transport"] == "stdio"
    assert "agentlab.rag_agent.mcp.knowledge_server" in " ".join(
        config["agentlab"]["args"]
    )
    assert "agentlab.rag_agent.mcp.utils_server" in " ".join(config["utils"]["args"])
    assert config["agentlab"]["cwd"]


def test_build_mcp_config_streamable_http(monkeypatch):
    monkeypatch.setattr(mcp_client, "MCP_TRANSPORT", "streamable_http")
    config = mcp_client.build_mcp_config()
    assert config["agentlab"]["transport"] == "streamable_http"
    assert config["utils"]["transport"] == "streamable_http"
    assert config["agentlab"]["url"].endswith("/mcp")
    assert config["utils"]["url"].endswith("/mcp")
