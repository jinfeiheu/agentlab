# MCP 客户端配置

本项目提供两个 MCP server，全部是公开、只读工具：

| server | 脚本 | 工具 |
|---|---|---|
| `agentlab` | `mcp_server.py` | `search_docs`、`list_sources`、`doc_stats` |
| `utils` | `mcp_utils_server.py` | `calculator`、`word_count` |

`mcp_client.py` 会同时连接两个 server 并聚合工具。项目 API 用 `USE_MCP=true` 启用聚合工具。

## stdio（本地，默认）

客户端以子进程方式启动 server，通过 stdin/stdout 通信，不占用端口。

Claude Desktop 的 `claude_desktop_config.json`、Claude Code 的项目 `.mcp.json`、Cursor 的 `.cursor/mcp.json` 都可以使用同一种结构：

```json
{
  "mcpServers": {
    "agentlab": {
      "command": "uv",
      "args": ["run", "python", "/home/jinfei/cc_test/langchain-demo/mcp_server.py"],
      "cwd": "/home/jinfei/cc_test/langchain-demo"
    },
    "utils": {
      "command": "uv",
      "args": ["run", "python", "/home/jinfei/cc_test/langchain-demo/mcp_utils_server.py"],
      "cwd": "/home/jinfei/cc_test/langchain-demo"
    }
  }
}
```

命令行验证：

```bash
uv run python mcp_client.py
# 工具: ['calculator', 'doc_stats', 'list_sources', 'search_docs', 'word_count']
```

## Streamable HTTP（远程/多客户端）

server 作为独立服务运行，客户端通过 URL 连接。先启动两个终端：

```bash
uv run python mcp_server.py --transport streamable-http --host 0.0.0.0 --port 8811
uv run python mcp_utils_server.py --transport streamable-http --host 0.0.0.0 --port 8812
```

LangChain 客户端：

```bash
MCP_TRANSPORT=streamable_http uv run python mcp_client.py
```

`mcp_client.build_mcp_config()` 会生成：

```python
{
    "agentlab": {"transport": "streamable_http", "url": "http://localhost:8811/mcp"},
    "utils": {"transport": "streamable_http", "url": "http://localhost:8812/mcp"},
}
```

外部客户端（Claude Desktop/Code/Cursor）使用各自的 HTTP 配置格式，通常写 `url` 或 `type: "http"`，以客户端文档为准。生产环境必须在前面加 TLS、Bearer/OAuth 鉴权和限流；不要把只有内网权限的工具直接暴露到公网。

## stdio vs streamable HTTP

| | stdio | streamable HTTP |
|---|---|---|
| 进程 | 客户端拉起子进程 | 独立常驻服务 |
| 多客户端 | 每个客户端一份 | 共享 |
| 网络/鉴权 | 无端口，继承本地权限 | 需要 TLS、鉴权、限流 |
| 部署 | 本机命令 | 容器/服务 + 端口 |
| 适用 | IDE、桌面客户端、本地工具 | 团队共享、远程 Agent、多实例 |

默认用 stdio；需要跨机器、多客户端共享或独立扩缩容时再切 HTTP。

## 权限边界

公共 MCP 只暴露知识库和纯工具：

- 不暴露 `tickets`、`memory` 等按用户隔离的数据；
- 不暴露写操作（发送报告、修改数据）——`send_report` 仍留在 API 进程内做 HITL；
- HTTP 模式必须自行加鉴权，不能依赖“内网”作为安全边界。

## 什么时候不该用 MCP

只有一个工具、只在一个 Python 进程里调用时，本地函数更简单、更快、类型更安全。MCP 的价值在协议边界：多客户端复用、跨语言、独立部署、多 server 聚合和权限隔离。本项目保留 `make_search_tool` 作为本地路径，MCP 是可选边界。
