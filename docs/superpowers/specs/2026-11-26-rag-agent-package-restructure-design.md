# RAG Agent 包结构分层设计

- **日期**：2026-11-26
- **状态**：Proposed（待确认）
- **关联**：
  - `README.md`
  - `tests/test_package_layout.py`
  - `docs/superpowers/plans/2026-10-28-agentlab-package-refactor.md`（上一轮包重构）
- **决策**：采用“产品优先”的包结构；第二条产品线命名为 `rag_agent`。

## 1. 背景

当前 `agentlab/` 的顶层把两条产品线混在一起：

- `analytics/` 是一个完整的产品包（Text-to-SQL）；
- RAG / Conversational Agent 分散在 `agent/`、`rag/`、`tools/`、`mcp/`、`cli.py` 五处；
- `api/` 同时承载两条线：`app.py` 一个文件里既挂 `/chat*` 又挂 `/analytics/*`，`sse.py` / `services.py` 只服务 RAG，`analytics.py` 只服务 Analytics，`schemas.py` 两边混放，`static/` 下两个页面也混放；
- 共享基础设施 `config.py`、`models.py`、`security/`、`observability/` 没有显式标记。

结果是：面试官或新同事打开仓库，第一眼看到的是“一个 analytics 包 + 一堆平铺模块”，而不是“两条产品线 + 一个 API 组装层 + 共享基础设施”。

**目标读者**：面试官 / 同事在仓库里快速建立心智模型。  
**不是目标**：拆成两个可独立部署的服务或两个 PyPI 包。

## 2. 目标与非目标

### 目标

1. 顶层目录一眼能看出两条产品线：`analytics/` 与 `rag_agent/`。
2. 每条产品线自己拥有 agent 图、检索/工具、CLI 等实现。
3. `api/` 变成纯粹的组装层：`app.py` 只做 app 工厂、lifespan、鉴权、健康检查和静态页；两条线的路由/服务/schema 放在 `api/<product>/` 下。
4. 共享基础设施继续放在顶层，并在 README 中明确标注为 shared。
5. 所有现有行为保持不变：URL、SSE 事件名、CLI 命令、MCP 工具名、测试断言语义。
6. 现有 457 个测试（430 passed / 27 skipped）继续通过；新增 1 个结构守卫测试后为 458 collected / 431 passed / 27 skipped。

### 非目标

- 不拆独立部署，不引入两个 pyproject / 两个 Dockerfile。
- 不改 `analytics/` 的内部结构与实现。
- 不改任何 HTTP 路由路径、SSE 事件名或数据库 schema。
- 不在本轮重命名 `eval/`、`tests/` 下的文件（第二阶段可选）。
- 不重写历史计划、历史 spec、`docs/archive/`。

### 反目标

- 为了“看起来分层”引入 `products/analytics` + `products/rag_agent` + `platform/` 的多层嵌套；单仓单部署没有收益，只增加 import 长度。
- 保留旧路径的兼容 shim（`agentlab/agent/...` 再 re-export）；这会重新制造“目录看不出层次”的问题。
- 把 `analytics/` 改名为 `data_qa/` 之类；现有名字已经清晰，改动只会增加无谓 diff。

## 3. 方案对比

### 方案 A：产品优先结构 + 按产品拆 API（选中）

- RAG 线整体迁入 `agentlab/rag_agent/`，内部保持 `graph.py / multi_agent.py / memory.py / context.py` + `rag/` + `tools/` + `mcp/` + `cli.py`。
- `agentlab/api/` 拆成 `app.py`（组装根）+ `deps.py` + `rag_agent/` + `analytics/`。
- 共享基础设施留在顶层。

**优点**：顶层直接呈现两条产品线；API 不再混两条线；每个产品包自包含；interviewer 的阅读路径最短。  
**代价**：几十个文件的 import 机械更新；需要同步测试 patch 目标和文档；中等工作量。

### 方案 B：只拆 API + 改 `agent/` 名字

- 保留 `rag/`、`tools/`、`mcp/` 在顶层，只把 `agent/` 改名并把 `api/` 拆分。

**优点**：改动小、风险低。  
**缺点**：顶层仍然是 `analytics` 对 `assistant` + `rag` + `tools` + `mcp`，第二条线还是散的；面试官第一眼只能看懂一半。不选。

### 方案 C：`products/` + `platform/`

- `agentlab/products/analytics/`、`agentlab/products/rag_agent/`、`agentlab/platform/`。

**优点**：层次最显式。  
**缺点**：对单仓、单部署的作品集只是多一层嵌套；import 变长，收益低。不选。

### 命名：为什么是 `rag_agent`

| 名字 | 定位准确性 | 优点 | 问题 |
|---|---|---|---|
| `rag_agent/`（选中） | 中高 | 面试官秒懂 RAG；与 `agentlab-analytics` 形成 `agentlab-rag` 对称；不和 `analytics/` 混淆 | 技术标签优先于产品标签；MCP/记忆/多 Agent 是支撑能力 |
| `knowledge/` | 高 | 与 `analytics/` 同为领域名；“数据问答 vs 知识问答”叙事好 | 用户最终选择更直白的 RAG 标签 |
| `assistant/` | 低 | 通用 | 两条线都是 assistant，无法区分 |
| `research/` | 低 | 有探索感 | 固定语料、不联网，overclaim |
| `support/` | 低 | 贴合 tickets | 只是工具之一，过窄 |

**决策**：目录用 `rag_agent/`；README 产品名写 “RAG / Conversational Agent”，保留“知识问答”作为一句话定位。CLI canonical 命令用 `agentlab-rag`，`agentlab` 保留为兼容别名。

## 4. 目标结构

```text
agentlab/
├── __init__.py
├── __main__.py                      # -> rag_agent.cli.main
├── config.py                        # shared
├── models.py                        # shared
├── analytics/                       # 产品一：Text-to-SQL（内部不动）
│   ├── graph.py
│   ├── multi_agent.py
│   ├── sql_guard.py
│   ├── ...
│   └── cli.py
├── rag_agent/                       # 产品二：RAG / Conversational Agent
│   ├── __init__.py
│   ├── graph.py
│   ├── multi_agent.py
│   ├── memory.py
│   ├── context.py
│   ├── cli.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── ingest.py
│   │   ├── loaders.py
│   │   └── retrieval.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── builtin.py
│   │   └── tickets.py
│   └── mcp/
│       ├── __init__.py
│       ├── client.py
│       ├── knowledge_server.py
│       └── utils_server.py
├── api/                             # 只做组装
│   ├── __init__.py
│   ├── app.py                       # create_app / lifespan / login / healthz / static
│   ├── deps.py                      # auth 依赖、服务依赖、限流、thread lock
│   ├── auth_schemas.py              # LoginRequest / LoginResponse
│   ├── redaction.py                 # 共享的递归脱敏 helper
│   ├── streaming.py                 # 共享的 sse() / _refusal_events()
│   ├── rag_agent/
│   │   ├── __init__.py
│   │   ├── routes.py                # /chat, /chat/stream, /chat/resume, /chat/stream/resume
│   │   ├── schemas.py               # ChatRequest / ChatResponse / ResumeRequest
│   │   ├── services.py              # Services, build_services, thread repair, memory hooks
│   │   └── sse.py                   # RAG 专属 SSE 事件映射
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── routes.py                # /analytics/chat, /analytics/chat/stream, /analytics/cancel
│   │   ├── schemas.py               # Analytics* request/response
│   │   ├── services.py              # AnalyticsServices, build_analytics_services
│   │   └── events.py                # analytics_events / step 事件 / audit stream
│   └── static/
│       ├── rag_agent.html           # 原 index.html
│       └── analytics.html
├── security/                        # shared
└── observability/                   # shared
```

## 5. 文件映射

### 5.1 领域包

| 旧路径 | 新路径 |
|---|---|
| `agentlab/agent/graph.py` | `agentlab/rag_agent/graph.py` |
| `agentlab/agent/multi_agent.py` | `agentlab/rag_agent/multi_agent.py` |
| `agentlab/agent/memory.py` | `agentlab/rag_agent/memory.py` |
| `agentlab/agent/context.py` | `agentlab/rag_agent/context.py` |
| `agentlab/agent/__init__.py` | `agentlab/rag_agent/__init__.py` |
| `agentlab/rag/loaders.py` | `agentlab/rag_agent/rag/loaders.py` |
| `agentlab/rag/retrieval.py` | `agentlab/rag_agent/rag/retrieval.py` |
| `agentlab/rag/ingest.py` | `agentlab/rag_agent/rag/ingest.py` |
| `agentlab/rag/__init__.py` | `agentlab/rag_agent/rag/__init__.py` |
| `agentlab/tools/builtin.py` | `agentlab/rag_agent/tools/builtin.py` |
| `agentlab/tools/tickets.py` | `agentlab/rag_agent/tools/tickets.py` |
| `agentlab/tools/__init__.py` | `agentlab/rag_agent/tools/__init__.py` |
| `agentlab/mcp/client.py` | `agentlab/rag_agent/mcp/client.py` |
| `agentlab/mcp/knowledge_server.py` | `agentlab/rag_agent/mcp/knowledge_server.py` |
| `agentlab/mcp/utils_server.py` | `agentlab/rag_agent/mcp/utils_server.py` |
| `agentlab/mcp/__init__.py` | `agentlab/rag_agent/mcp/__init__.py` |
| `agentlab/cli.py` | `agentlab/rag_agent/cli.py` |
| `agentlab/__main__.py` | 保留，import 改为 `rag_agent.cli` |

### 5.2 API 层

| 旧路径 | 新路径 |
|---|---|
| `agentlab/api/app.py` 的 chat 路由 | `agentlab/api/rag_agent/routes.py` |
| `agentlab/api/app.py` 的 analytics 路由 | `agentlab/api/analytics/routes.py` |
| `agentlab/api/app.py` 的依赖函数 | `agentlab/api/deps.py` |
| `agentlab/api/sse.py` 的 `sse()` / `_refusal_events()` | `agentlab/api/streaming.py` |
| `agentlab/api/sse.py` 的 RAG 专属事件映射 | `agentlab/api/rag_agent/sse.py` |
| `agentlab/api/services.py` | `agentlab/api/rag_agent/services.py` |
| `agentlab/api/analytics.py` | 拆为 `agentlab/api/analytics/services.py` + `events.py` |
| `agentlab/api/schemas.py` 的 chat 模型 | `agentlab/api/rag_agent/schemas.py` |
| `agentlab/api/schemas.py` 的 analytics 模型 | `agentlab/api/analytics/schemas.py` |
| `agentlab/api/schemas.py` 的 login 模型 | `agentlab/api/auth_schemas.py` |
| `agentlab/api/static/index.html` | `agentlab/api/static/rag_agent.html` |
| `agentlab/api/static/analytics.html` | 保留 |

### 5.3 入口与配置

| 位置 | 变更 |
|---|---|
| `pyproject.toml` `agentlab` | `agentlab.rag_agent.cli:main`（兼容别名） |
| `pyproject.toml` `agentlab-rag` | 新增，`agentlab.rag_agent.cli:main`（canonical） |
| `pyproject.toml` `agentlab-mcp-knowledge` | `agentlab.rag_agent.mcp.knowledge_server:main` |
| `pyproject.toml` `agentlab-mcp-utils` | `agentlab.rag_agent.mcp.utils_server:main` |
| `agentlab/rag_agent/mcp/client.py` | stdio args 改为 `agentlab.rag_agent.mcp.*` |
| `agentlab/rag_agent/mcp/knowledge_server.py` / `utils_server.py` | 仅随包移动，不改行为 |

## 6. API 拆分设计

### 6.1 组装根 `api/app.py`

保留：

- `STATIC_DIR`
- `create_app(services=None, analytics=None)`
- lifespan：初始化 tracing、`build_services()`、`build_analytics_services()`；关闭时调用 `aclose()` 和 `shutdown_tracing()`
- `GET /login`
- `GET /healthz`
- `GET /` -> `static/rag_agent.html`
- `GET /analytics` -> `static/analytics.html`
- `app = create_app()`
- `serve()`

`create_app` 把测试需要 patch 的常量读入 app state：

- `app.state.request_timeout = REQUEST_TIMEOUT`
- `app.state.limiter = RateLimiter(RATE_LIMIT_PER_MINUTE)`
- `app.state.thread_locks = {}`
- `app.state.analytics_tasks = {}`

这样 `tests/test_api.py` 仍可 patch `agentlab.api.app.REQUEST_TIMEOUT` / `RATE_LIMIT_PER_MINUTE`，然后调用 `create_app()`。

`app.py` 仍需在模块命名空间保留以下名字，避免测试 patch 目标失效：

- `build_services`（从 `api.rag_agent.services` import）
- `setup_tracing` / `shutdown_tracing`
- `REQUEST_TIMEOUT` / `RATE_LIMIT_PER_MINUTE`
- `RateLimiter`（从 `api.deps` import）

### 6.2 `api/deps.py`

移动以下内容：

- `RateLimiter`
- `get_current_user`
- `get_services`
- `get_analytics_services`
- `get_thread_lock`

依赖模块不得 import `api.app`，避免环。

### 6.3 `api/rag_agent/`

- `routes.py`：`/chat`、`/chat/stream`、`/chat/resume`、`/chat/stream/resume` 四个端点，使用 `APIRouter`；从 `api.deps` 取依赖，从 `api.rag_agent.schemas` 取模型，从 `api.rag_agent.sse` 取事件生成器，从 `api.rag_agent.services` 取 thread repair / memory hooks。
- `schemas.py`：`ChatRequest`、`ChatResponse`、`ResumeRequest`。
- `services.py`：原 `api/services.py` 全部内容（`Services`、`build_services`、`_pending_tool_calls`、`_reset_thread`、`_prepare_thread`、`_maybe_extract_memory`、`_post_turn_memory`）。
- `sse.py`：原 `api/sse.py` 中 RAG 专属的事件映射（`_extract_answer`、`_extract_sources`、`_get_interrupt`、`_has_interrupt`、`_tool_events`、`_chat_events`）；`sse` / `_refusal_events` 从 `api.streaming` import。

### 6.4 `api/analytics/`

- `routes.py`：`/analytics/chat`、`/analytics/chat/stream`、`/analytics/cancel`；`_analytics_response` 从 `app.py` 移入。
- `schemas.py`：`AnalyticsChatRequest`、`AnalyticsChatResponse`、`AnalyticsCancelRequest`、`AnalyticsCancelResponse`。
- `services.py`：`AnalyticsServices`、`build_analytics_services`。
- `events.py`：`DEFAULT_STEPS`、`analytics_events`、`_step_summary`、`_audit_stream`；`sse` 从 `api.streaming` import。
- `routes.py` 的流式拒绝分支从 `api.streaming` import `_refusal_events`。

### 6.5 共享 API 工具

**脱敏**：`api/sse.py` 和 `api/analytics.py` 各有一份 `_redact_value`。本轮抽到 `api/redaction.py`，提供 `redact_value(value)`：

- `api/rag_agent/sse.py` 用它处理 tool args/result；
- `api/analytics/events.py` 用它处理 `final` 事件的 rows/chart_spec；
- `api/analytics/routes.py` 用它处理 `_analytics_response`。

行为不变，只是去掉重复实现。

**流式原语**：`sse()` 与 `_refusal_events()` 同时被 RAG 和 Analytics 使用（`api/analytics.py` 的事件生成、`api/app.py` 两条 `/stream` 的拒绝分支）。它们不属于任何一条产品线，移到 `api/streaming.py`：

- `api/rag_agent/sse.py` 只保留 RAG 专属事件映射，从 `api.streaming` import `sse`；
- `api/analytics/events.py` 和 `api/analytics/routes.py` 从 `api.streaming` import `sse` / `_refusal_events`；
- 这样 Analytics API 不依赖 `api.rag_agent`，两条产品线的 API 包保持对等。

### 6.6 路由不变量

以下路径、方法和 SSE 事件名保持不变：

- `POST /login`、`GET /healthz`、`GET /`、`GET /analytics`
- `POST /chat`、`POST /chat/stream`、`POST /chat/resume`、`POST /chat/stream/resume`
- `POST /analytics/chat`、`POST /analytics/chat/stream`、`POST /analytics/cancel`
- SSE：`token`、`tool_call`、`tool_result`、`interrupt`、`error`、`done`；`plan_created`、`step_started`、`step_result`、`verification`、`replan`、`final`

## 7. import 迁移规则

按模块前缀替换，且只替换 RAG 线：

- `agentlab.agent.*` -> `agentlab.rag_agent.*`
- `agentlab.rag.*` -> `agentlab.rag_agent.rag.*`
- `agentlab.tools.*` -> `agentlab.rag_agent.tools.*`
- `agentlab.mcp.*` -> `agentlab.rag_agent.mcp.*`
- `agentlab.cli` -> `agentlab.rag_agent.cli`
- `agentlab.api.sse` 的 `sse()` / `_refusal_events()` -> `agentlab.api.streaming`；RAG 专属事件映射 -> `agentlab.api.rag_agent.sse`
- `agentlab.api.services` -> `agentlab.api.rag_agent.services`
- `agentlab.api.schemas` -> 按模型类型拆到 `api.auth_schemas` / `api.rag_agent.schemas` / `api.analytics.schemas`
- `agentlab.api.analytics` -> `agentlab.api.analytics.services` 或 `.events`

**不动的 import**：

- `agentlab.analytics.*`
- `agentlab.config`
- `agentlab.models`
- `agentlab.security.*`
- `agentlab.observability.*`

**注意前缀陷阱**：`agentlab.rag_agent` 以 `agentlab.rag` 开头，替换时用完整模块名或带点的前缀，不要用裸字符串替换。

受影响的源码/测试/评测文件（grep 结果）：

- 源码：`agentlab/__main__.py`、`agentlab/agent/*`、`agentlab/mcp/*`、`agentlab/rag/*`、`agentlab/tools/*`、`agentlab/cli.py`、`agentlab/api/{app,services,sse,analytics}.py`
- 测试：`test_analytics_api.py`、`test_analytics_failure.py`、`test_api.py`、`test_api_modules.py`、`test_context.py`、`test_eval_data.py`、`test_eval_hard.py`、`test_graph.py`、`test_ingest.py`、`test_mcp.py`、`test_mcp_multi.py`、`test_memory.py`、`test_multi_agent.py`、`test_package_layout.py`、`test_persistence.py`、`test_rag.py`、`test_rerank.py`、`test_retrieval.py`、`test_tickets.py`、`test_tools.py`、`test_main.py`

这份清单是指示性的，不是穷尽的；实施时以 repo-wide search 为准，尤其是 `from agentlab.api import analytics`、`agentlab.api.sse`、`agentlab.api.services` 这类间接引用。
- 评测：`eval/run_eval.py`、`eval/text_metrics.py`

## 8. 测试与结构守卫

### 8.1 `tests/test_package_layout.py`

更新：

- `test_core_modules_import_under_package`：`agentlab.rag_agent.*`、`agentlab.rag_agent.rag.*`、`agentlab.rag_agent.tools.*`。
- `test_entrypoint_modules_import`：`agentlab.rag_agent.cli`、`agentlab.rag_agent.mcp.*`。
- `test_console_scripts_declared`：`agentlab` 和 `agentlab-rag` 都指向 `agentlab.rag_agent.cli:main`；MCP 脚本指向新路径。
- `test_static_index_exists`：改查 `rag_agent.html`。

新增：

- `test_no_legacy_moved_imports`：用 AST 扫描 `.py`，禁止以下模块（含其子模块）：
  - `agentlab.agent`
  - `agentlab.rag`
  - `agentlab.tools`
  - `agentlab.mcp`
  - `agentlab.cli`
  - `agentlab.api.sse`
  - `agentlab.api.services`
  - `agentlab.api.schemas`

判断用 `module == moved or module.startswith(moved + ".")`，避免把 `agentlab.rag_agent` 误判为 `agentlab.rag`。

### 8.2 测试 patch 目标

重点文件：

- `tests/test_api.py`
  - `import agentlab.api.services as api_services` -> `agentlab.api.rag_agent.services`
  - `from agentlab.api.services import ...` -> `agentlab.api.rag_agent.services`
  - `from agentlab.api.sse import ...` -> `agentlab.api.rag_agent.sse`
  - `monkeypatch.setattr(api, "build_services", ...)` / `REQUEST_TIMEOUT` / `RATE_LIMIT_PER_MINUTE` / `setup_tracing` / `shutdown_tracing` 保持，因为 `api.app` 仍持有这些名字。
- `tests/test_api_modules.py`
  - schema / services / sse 的 import 改为新路径。
- `tests/test_analytics_api.py`
  - `from agentlab.api.analytics import AnalyticsServices` -> `from agentlab.api.analytics.services import AnalyticsServices`
  - `monkeypatch.setattr("agentlab.api.analytics.write_audit", ...)` -> `"agentlab.api.analytics.events.write_audit"`
- `tests/test_analytics_failure.py`
  - `from agentlab.api import analytics as analytics_api` -> `from agentlab.api.analytics import events`
  - `analytics_api.analytics_events(...)` -> `events.analytics_events(...)`
  - `monkeypatch.setattr(analytics_api, "write_audit", ...)` -> `monkeypatch.setattr(events, "write_audit", ...)`
- `tests/test_main.py`
  - `from agentlab import cli as main` -> `from agentlab.rag_agent import cli as main`
- 其余 RAG 测试：只改 import，不改断言。

以上清单同样是指示性的；实施时用 repo-wide grep 找 `agentlab.api.analytics`、`agentlab.api.sse`、`agentlab.api.services` 的所有引用，避免遗漏 `tests/test_analytics_failure.py` 这类间接 import。

### 8.3 不在本轮做

- 测试文件名对称化（`test_graph.py` -> `test_rag_agent_graph.py` 等）。
- `eval/run_eval.py` -> `eval/run_rag_agent_eval.py`。
- `eval/golden.jsonl` -> `eval/rag_agent_golden.jsonl`。

这些留到第二阶段，避免本轮 diff 过大。若做，必须同步 `agentlab/config.py` 的路径常量、README、`docs/results/` 引用。

## 9. 文档更新

必须更新：

- `README.md`
  - “目录结构”整段替换为新树。
  - 快速开始、API、MCP、多 Agent、代码入口里的旧路径。
  - 静态页路径 `static/index.html` -> `static/rag_agent.html`。
  - 测试数量：重构前 457 collected / 430 passed / 27 skipped；新增 guard 后 458 / 431 / 27，README 同步更新。
  - 把“RAG 是 Analytics API 的基础设施来源”改为“两条线共享 auth/streaming/guard/tracing 模块”，避免误导为 Analytics 依赖 `rag_agent` 包。
- `docs/mcp-clients.md`
  - `python -m agentlab.mcp.*` -> `python -m agentlab.rag_agent.mcp.*`
- `docs/interview-notes.md`
  - RAG 线代码入口路径。
- `docs/CHANGELOG.md`
  - 新增 2026-11-26 条目：包结构分层。

必须更新（脚本）：

- `scripts/demo.sh`：`python -m agentlab.rag.ingest` -> `python -m agentlab.rag_agent.rag.ingest`；`python -m agentlab.mcp.client` -> `python -m agentlab.rag_agent.mcp.client`；打印的 MCP 命令同步。
- 其它脚本只用 `uv run agentlab`（兼容别名）或 analytics 模块，不需要改。

不更新：

- `docs/archive/`
- `docs/superpowers/plans/` 与 `docs/superpowers/specs/` 下的历史文档
- `eval/results/`、`docs/results/` 的历史结果

可选顺手修复（独立提交，不算本设计范围）：

- README “已知限制”第 8 条“仓库没有 GitHub Actions”已过时。
- README “已知限制”第 10 条“多步计划尚未接线”与 `--plan` 已接线不一致。

## 10. 行为不变量

- `analytics/` 源码零改动。
- 所有 HTTP 路径、SSE 事件名、请求/响应字段不变。
- `agentlab`、`agentlab-analytics`、`agentlab-api` 命令继续可用；新增 `agentlab-rag` 作为 RAG 线的显式命令。
- `python -m agentlab` 仍启动 RAG CLI。
- MCP server 名称仍为 `agentlab` / `utils`，工具名不变；只改子进程模块路径。
- 数据库 schema、seed、审计表不变。
- 页面 `/`、`/analytics` 的 URL 不变。
- 测试断言语义不变，只改 import 与 patch 目标。

## 11. 实施顺序

1. **基线**：`uv run pytest -q` 记录 `430 passed, 27 skipped`；确认 `git status` 干净。
2. **移动 RAG 领域包**：`git mv` 到 `agentlab/rag_agent/`；补 `__init__.py`；更新包内 import。
3. **拆分 API**：创建 `api/deps.py`、`api/redaction.py`、`api/auth_schemas.py`、`api/rag_agent/`、`api/analytics/`；移动路由/服务/schema/sse/static；重写 `api/app.py` 为组装根。
4. **入口**：更新 `pyproject.toml`、`agentlab/__main__.py`、MCP stdio args。
5. **测试**：更新 import、patch 目标、`test_package_layout.py`，新增 legacy import guard。
6. **文档**：README、mcp-clients、interview-notes、CHANGELOG。
7. **验证**：见第 12 节。

建议 commit 拆分（便于 review 和回滚）：

1. `refactor(rag_agent): move RAG domain package`
2. `refactor(api): split composition root and product routers`
3. `test: update imports and add layout guard`
4. `docs: update paths for rag_agent package`

## 12. 验证

必须通过：

```bash
uv run pytest -q                       # 431 passed, 27 skipped（458 collected；基线为 430/27/457）
uv run pytest -q tests/test_package_layout.py
uv run python -m compileall -q agentlab
uv run python -c "import agentlab.api.app, agentlab.rag_agent.cli, agentlab.rag_agent.graph, agentlab.rag_agent.mcp.client"
```

手工检查：

- `uv run python -c "from agentlab.api.app import create_app; app=create_app(); print(sorted({r.path for r in app.routes}))"` 路由集合与重构前一致。
- `grep -rn "agentlab\.agent\|agentlab\.rag\.\|agentlab\.tools\|agentlab\.mcp\|agentlab\.cli\|agentlab\.api\.sse\|agentlab\.api\.services\|agentlab\.api\.schemas" agentlab eval tests scripts` 无残留（`agentlab.rag_agent.*`、`agentlab.api.rag_agent.*` 除外）。
- `git diff --stat` 中没有非预期文件（如 `uv.lock`、`eval/results/`）。

不要求：

- 50 条 Analytics eval、压测、集成测试。它们依赖 API Key / Postgres，和包结构无关；如需回归，单独跑 `bash scripts/ci_analytics.sh`。

## 13. 风险与缓解

| 风险 | 缓解 |
|---|---|
| import 漏改 | `test_no_legacy_moved_imports` + `pytest` + `compileall` |
| 文件清单遗漏（如 `test_analytics_failure.py`） | 以 repo-wide grep/AST 为准；不依赖文档清单；新增 legacy import guard |
| Analytics API 反向依赖 RAG API | `sse()` / `_refusal_events()` 放 `api/streaming.py`；`api/analytics/*` 不 import `api/rag_agent/*` |
| API 拆分引入循环 import | `api/deps.py` 只依赖服务模块，不依赖 `api.app`；路由不 import app |
| 测试 patch 目标失效导致真实副作用 | 逐文件更新 patch 字符串；跑全量测试；重点检查 `test_api.py` / `test_analytics_api.py` / `test_analytics_failure.py` |
| `REQUEST_TIMEOUT` / `RATE_LIMIT_PER_MINUTE` patch 失效 | `create_app` 从 `api.app` 模块常量读入 app state；路由只读 app state |
| 静态页改名破坏测试/文档 | 更新 `test_static_index_exists` 与 README；`/` 路由保持不变 |
| `scripts/demo.sh` 失效 | 同步更新脚本命令；验证 grep 覆盖 `scripts/` |
| MCP 子进程找不到模块 | 更新 `MCP_SERVER_CONFIG` args；`test_mcp.py` / `test_mcp_multi.py` 断言新路径 |
| 把 `agentlab.rag_agent` 误替换成 `agentlab.rag` | 使用带点前缀匹配；替换后跑 guard test |
| 文档遗漏 | README 全量搜索旧路径；历史文档明确不更新 |

## 14. 留给 builder 的决定

以下不需要产品决策，builder 可自行处理：

- 每个 `__init__.py` 的 docstring 文案。
- `api/rag_agent/routes.py` 与 `api/analytics/routes.py` 的函数拆分粒度（只要路由集合与行为不变）。
- `api/redaction.py` 的函数命名（建议 `redact_value`）。
- commit 的具体拆分方式。
- 是否在本轮顺手修正 README 的两处过时“已知限制”（建议单独提交）。

需要产品/用户确认的只有：本设计是否批准。批准后进入实施计划（`superpowers:writing-plans`）。

## 15. Builder check resolutions（2026-11-26）

1. **SSE 原语位置**：采纳共享 `api/streaming.py`；Analytics API 不 import `api.rag_agent`。
2. **affected-file 清单**：以 repo-wide search 为准；补入 `tests/test_analytics_failure.py`；不添加兼容 re-export。
3. **`scripts/demo.sh`**：纳入本轮；同步模块路径，并把 `scripts/` 纳入验证 grep。
4. **测试数量**：新增独立 guard test，预期 458 collected / 431 passed / 27 skipped；README 同步更新。
