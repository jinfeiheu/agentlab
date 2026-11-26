# RAG Agent 包结构分层 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 AgentLab 重排成 `analytics/` + `rag_agent/` 两条产品线 + `api/` 组装层 + 顶层共享基础设施，行为、路由、CLI 命令与 MCP 工具名全部不变。

**Architecture:** RAG 线（agent 图、rag、tools、mcp、cli）整体迁入 `agentlab/rag_agent/`；`agentlab/api/` 拆成 `app.py`（组装根）、`deps.py`、`streaming.py`、`redaction.py`、`auth_schemas.py`，以及 `api/rag_agent/`、`api/analytics/` 两个产品子包。`analytics/` 源码不动。

**Tech Stack:** Python 3.12、LangGraph、FastAPI、pytest、uv、hatchling。

**Spec:** `docs/superpowers/specs/2026-11-26-rag-agent-package-restructure-design.md`

## Global Constraints

- 行为不变：所有 HTTP 路径、SSE 事件名、请求/响应字段、CLI 参数、MCP server/tool 名保持原样。
- `agentlab/analytics/` 源码零改动；只允许更新测试与文档中的 import。
- 单仓、单部署；共享代码允许，但不引入 `products/` / `platform/` 多层。
- 不保留旧模块路径的兼容 shim；干净移动。
- 历史文档 `docs/archive/`、`docs/superpowers/plans/`、`docs/superpowers/specs/` 不重写。
- 基线：`457 collected / 430 passed / 27 skipped`。新增一个结构守卫测试后：`458 / 431 / 27`。
- Python 3.12；测试命令统一 `uv run pytest -q`。
- 每个 commit message 末尾加 `Co-Authored-By: Claude Code <noreply@anthropic.com>`。

## Review Focus

- `scripts/demo.sh` 和 `docs/mcp-clients.md` 仍使用旧模块路径 → 文档里的 demo/MCP 命令会直接失败。由 Task 7 扩展 `test_no_legacy_moved_imports` 的文本检查覆盖。
- `tests/test_analytics_failure.py` 直接 import `agentlab.api.analytics` 并 patch `write_audit` → 漏改会让测试写真实 Postgres。Task 4 显式迁移并用全量测试验证。
- `tests/test_api.py` 通过 `api_services` 模块 patch `USE_DB/RAG_MODE/USE_MCP` → 模块搬家后 patch 不生效，测试会静默用真实默认值。Task 3 显式迁移并用全量测试验证。
- `agentlab/__main__.py` 与 `pyproject` console scripts → 入口漏改会让 `python -m agentlab` / `agentlab` 直接 ImportError。Task 1 的 `test_entrypoint_modules_import` 与 `test_console_scripts_declared` 覆盖。
- MCP stdio 子进程参数 `-m agentlab.mcp.*` → 漏改会导致 MCP demo 启动失败。Task 1 的 `test_mcp.py` / `test_mcp_multi.py` 覆盖。

---

### Task 1: 移动 RAG 领域包并修正所有 import 与入口

**Files:**
- Move: `agentlab/agent/` → `agentlab/rag_agent/`；`agentlab/rag/` → `agentlab/rag_agent/rag/`；`agentlab/tools/` → `agentlab/rag_agent/tools/`；`agentlab/mcp/` → `agentlab/rag_agent/mcp/`；`agentlab/cli.py` → `agentlab/rag_agent/cli.py`
- Modify: `agentlab/rag_agent/**/*.py`、`agentlab/api/{app,services,sse,analytics}.py`、`agentlab/__main__.py`、`eval/run_eval.py`、`eval/text_metrics.py`、`tests/*.py`
- Modify: `pyproject.toml:26-31`
- Test: `tests/test_package_layout.py`、`tests/test_mcp.py`、`tests/test_mcp_multi.py`、`tests/test_main.py`

**Interfaces:**
- Produces: `agentlab.rag_agent.cli.main`、`agentlab.rag_agent.graph.build_graph`、`agentlab.rag_agent.rag.retrieval.build_pgvector_hybrid_retriever`、`agentlab.rag_agent.mcp.client.MCP_SERVER_CONFIG`。
- Consumes: 共享模块 `agentlab.config`、`agentlab.models`、`agentlab.security.*`、`agentlab.observability.*`；这些路径不变。

- [ ] **Step 1: 先把结构测试改成新路径，确认失败**

更新 `tests/test_package_layout.py`：

```python
from agentlab.rag_agent.context import estimate_tokens
from agentlab.rag_agent.graph import build_graph
from agentlab.rag_agent.memory import MemoryItem
from agentlab.rag_agent.multi_agent import build_multi_agent_graph
from agentlab.rag_agent.rag.ingest import build_vector_store
from agentlab.rag_agent.rag.loaders import load_documents
from agentlab.rag_agent.rag.retrieval import rrf_fuse
from agentlab.rag_agent.tools.builtin import calculator
from agentlab.rag_agent.tools.tickets import get_ticket
```

`test_entrypoint_modules_import` 改为：

```python
import agentlab.rag_agent.cli
import agentlab.api.app
import agentlab.rag_agent.mcp.client
import agentlab.rag_agent.mcp.knowledge_server
import agentlab.rag_agent.mcp.utils_server

assert callable(agentlab.rag_agent.cli.main)
```

`test_console_scripts_declared` 改为：

```python
assert scripts["agentlab"] == "agentlab.rag_agent.cli:main"
assert scripts["agentlab-rag"] == "agentlab.rag_agent.cli:main"
assert scripts["agentlab-mcp-knowledge"] == "agentlab.rag_agent.mcp.knowledge_server:main"
assert scripts["agentlab-mcp-utils"] == "agentlab.rag_agent.mcp.utils_server:main"
```

把 `tests/test_mcp.py`、`tests/test_mcp_multi.py` 中的 `agentlab.mcp.knowledge_server` / `agentlab.mcp.utils_server` 断言改为 `agentlab.rag_agent.mcp.*`。

Run: `uv run pytest tests/test_package_layout.py tests/test_mcp.py tests/test_mcp_multi.py -q`
Expected: FAIL，`ModuleNotFoundError: No module named 'agentlab.rag_agent'`。

- [ ] **Step 2: 用 `git mv` 移动目录**

```bash
git mv agentlab/agent agentlab/rag_agent
git mv agentlab/rag agentlab/rag_agent/rag
git mv agentlab/tools agentlab/rag_agent/tools
git mv agentlab/mcp agentlab/rag_agent/mcp
git mv agentlab/cli.py agentlab/rag_agent/cli.py
```

把 `agentlab/rag_agent/__init__.py` 的 docstring 改为 `"""RAG / Conversational Agent 子包。"""`。

- [ ] **Step 3: 一次性替换 import 前缀**

在仓库根目录运行：

```bash
uv run python - <<'PY'
from pathlib import Path
import re

roots = [Path("agentlab"), Path("eval"), Path("tests"), Path("scripts")]
patterns = [
    (r"\bagentlab\.rag\.", "agentlab.rag_agent.rag."),
    (r"\bagentlab\.agent\b", "agentlab.rag_agent"),
    (r"\bagentlab\.tools\b", "agentlab.rag_agent.tools"),
    (r"\bagentlab\.mcp\b", "agentlab.rag_agent.mcp"),
    (r"\bagentlab\.cli\b", "agentlab.rag_agent.cli"),
    (r"\bfrom agentlab import cli\b", "from agentlab.rag_agent import cli"),
]
for root in roots:
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        new = text
        for pattern, repl in patterns:
            new = re.sub(pattern, repl, new)
        if new != text:
            path.write_text(new, encoding="utf-8")
PY
```

顺序不能反：先替换 `agentlab.rag.`，再替换 `agentlab.agent`，否则会把新生成的 `agentlab.rag_agent` 再替换一次。`agentlab.rag_agent` 不含 `agentlab.rag.`（点号）和 `agentlab.agent`（点号），所以脚本是幂等的。

- [ ] **Step 4: 更新入口与 MCP 配置**

`pyproject.toml` 的 `[project.scripts]` 改为：

```toml
agentlab = "agentlab.rag_agent.cli:main"
agentlab-rag = "agentlab.rag_agent.cli:main"
agentlab-api = "agentlab.api.app:serve"
agentlab-mcp-knowledge = "agentlab.rag_agent.mcp.knowledge_server:main"
agentlab-mcp-utils = "agentlab.rag_agent.mcp.utils_server:main"
agentlab-analytics = "agentlab.analytics.cli:main"
```

确认 `agentlab/__main__.py` 已由脚本改为 `from agentlab.rag_agent.cli import main`；确认 `agentlab/rag_agent/mcp/client.py` 的 stdio args 已是 `agentlab.rag_agent.mcp.knowledge_server` / `agentlab.rag_agent.mcp.utils_server`。

Run: `uv run python -m compileall -q agentlab eval tests`
Expected: 无输出、退出码 0。

- [ ] **Step 5: 全量测试**

Run: `uv run pytest -q`
Expected: `430 passed, 27 skipped`。

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(rag_agent): move RAG domain package

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 2: 抽出共享 API 工具与依赖模块

**Files:**
- Create: `agentlab/api/streaming.py`、`agentlab/api/redaction.py`、`agentlab/api/auth_schemas.py`、`agentlab/api/deps.py`
- Modify: `agentlab/api/sse.py`、`agentlab/api/analytics.py`、`agentlab/api/app.py`、`agentlab/api/schemas.py`
- Test: `tests/test_api_modules.py`

**Interfaces:**
- Produces:
  - `agentlab.api.streaming.sse(payload: dict) -> str`
  - `agentlab.api.streaming._refusal_events(message: str)` → async generator
  - `agentlab.api.redaction.redact_value(value) -> Any`
  - `agentlab.api.auth_schemas.LoginRequest` / `LoginResponse`
  - `agentlab.api.deps.RateLimiter`、`get_current_user`、`get_services`、`get_analytics_services`、`get_thread_lock`
- Consumes: `agentlab.api.services.Services`、`agentlab.api.analytics.AnalyticsServices`（Task 4 前仍在旧位置）。

- [ ] **Step 1: 更新已有测试的 import，确认失败（不新增测试函数）**

修改 `tests/test_api_modules.py`：

- `test_schemas_and_services_are_split`：把 `LoginRequest` / `LoginResponse` 的 import 从 `agentlab.api.schemas` 改为 `agentlab.api.auth_schemas`。
- `test_streaming_and_thread_helpers_are_split`：增加：

```python
    from agentlab.api.redaction import redact_value
    from agentlab.api.streaming import sse

    assert sse({"type": "done"}) == 'data: {"type": "done"}\n\n'
    assert redact_value({"email": "a@b.com"}) == {"email": "[EMAIL]"}
```

Run: `uv run pytest tests/test_api_modules.py -q`
Expected: FAIL，`ModuleNotFoundError: No module named 'agentlab.api.streaming'`。

- [ ] **Step 2: 创建 `streaming.py` 与 `redaction.py`**

`agentlab/api/streaming.py` 从 `agentlab/api/sse.py:22-34` 复制 `sse()` 与 `_refusal_events()`，签名不变。

`agentlab/api/redaction.py` 把 `agentlab/api/sse.py:139-147` 的递归 `_redact_value` 复制为公开的 `redact_value(value)`；`api/sse.py` 和 `api/analytics.py` 中各自的 `_redact_value` 删除，改为 import `redact_value`。

- [ ] **Step 3: 创建 `auth_schemas.py` 并拆 login 模型**

把 `agentlab/api/schemas.py:6-16` 的 `LoginRequest`、`LoginResponse` 移到 `agentlab/api/auth_schemas.py`，从 `api/schemas.py` 删除。`api/app.py` 的 login 端点改为从 `api.auth_schemas` import。

- [ ] **Step 4: 创建 `deps.py`**

把 `agentlab/api/app.py` 的以下内容移到 `agentlab/api/deps.py`，函数体不变：

- `RateLimiter`（`app.py:64-86`）
- `get_current_user`（`app.py:89-102`）
- `get_services`（`app.py:105-113`）
- `get_analytics_services`（`app.py:116-121`）
- `get_thread_lock`（`app.py:124-131`）

`deps.py` 从 `agentlab.api.services` import `Services`，从 `agentlab.api.analytics` import `AnalyticsServices`（Task 4 后再改）。`app.py` 改为 `from agentlab.api.deps import ...`，并保留 `RateLimiter` 这个名字在 `api.app` 命名空间（`from agentlab.api.deps import RateLimiter`），避免测试/文档引用失效。`app.py` 继续保留 `setup_tracing` / `shutdown_tracing` / `REQUEST_TIMEOUT` / `RATE_LIMIT_PER_MINUTE` 的模块级 import；`tests/test_api.py` 直接 patch `agentlab.api.app` 上的这些名字。

- [ ] **Step 5: 更新调用方并跑全量测试**

`api/sse.py` 改为 `from agentlab.api.streaming import sse`；`api/analytics.py` 改为 `from agentlab.api.streaming import sse` 和 `from agentlab.api.redaction import redact_value`；`api/app.py` 的 `_refusal_events` 改为从 `api.streaming` import，`_analytics_response` 用 `redact_value`。

Run: `uv run pytest -q`
Expected: `430 passed, 27 skipped`。

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(api): extract shared streaming, redaction, auth schemas, deps

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 3: 拆分 RAG API 子包

**Files:**
- Create: `agentlab/api/rag_agent/__init__.py`、`schemas.py`、`routes.py`
- Move: `agentlab/api/services.py` → `agentlab/api/rag_agent/services.py`；`agentlab/api/sse.py` → `agentlab/api/rag_agent/sse.py`
- Modify: `agentlab/api/app.py`、`agentlab/api/schemas.py`
- Test: `tests/test_api.py`、`tests/test_api_modules.py`

**Interfaces:**
- Produces: `agentlab.api.rag_agent.routes.router`（`APIRouter`，四个 `/chat*` 端点）、`agentlab.api.rag_agent.services.Services/build_services`、`agentlab.api.rag_agent.sse._chat_events/_tool_events`、`agentlab.api.rag_agent.schemas.ChatRequest/ChatResponse/ResumeRequest`。
- Consumes: `agentlab.api.deps`、`agentlab.api.streaming`、`agentlab.api.redaction`、`agentlab.rag_agent.*`。

- [ ] **Step 1: 更新测试 import，确认失败**

`tests/test_api.py`：

```python
import agentlab.api.services as api_services   # 改为 agentlab.api.rag_agent.services
from agentlab.api.services import (...)          # 同上
from agentlab.api.sse import _chat_events, _tool_events  # 改为 agentlab.api.rag_agent.sse
```

`tests/test_api_modules.py`：把 `ChatRequest/ChatResponse/ResumeRequest` 的 import 从 `agentlab.api.schemas` 改为 `agentlab.api.rag_agent.schemas`；`Services/build_services` 改从 `agentlab.api.rag_agent.services`；`_chat_events/_tool_events` 改从 `agentlab.api.rag_agent.sse`。

Run: `uv run pytest tests/test_api.py tests/test_api_modules.py -q`
Expected: FAIL，`ModuleNotFoundError: No module named 'agentlab.api.rag_agent'`。

- [ ] **Step 2: 创建包并移动 services/sse**

```bash
mkdir -p agentlab/api/rag_agent
git mv agentlab/api/services.py agentlab/api/rag_agent/services.py
git mv agentlab/api/sse.py agentlab/api/rag_agent/sse.py
touch agentlab/api/rag_agent/__init__.py
```

更新 `api/rag_agent/sse.py` 的内部 import：`_post_turn_memory` / `_prepare_thread` 从 `agentlab.api.rag_agent.services` 导入。同步把 `api/deps.py` 的 `Services` import 改为 `from agentlab.api.rag_agent.services import Services`。

- [ ] **Step 3: 拆 chat schemas**

把 `agentlab/api/schemas.py` 的 `ChatRequest`、`ChatResponse`、`ResumeRequest` 移到 `agentlab/api/rag_agent/schemas.py`，从 `api/schemas.py` 删除。

- [ ] **Step 4: 创建 `routes.py`**

把 `agentlab/api/app.py` 中 `/chat`、`/chat/resume`、`/chat/stream/resume`、`/chat/stream` 四个 handler 原样搬入 `agentlab/api/rag_agent/routes.py`，放在 `router = APIRouter()` 上。替换规则：

- `app` -> `request.app`；`app.state.*` -> `request.app.state.*`
- `REQUEST_TIMEOUT` -> `request.app.state.request_timeout`
- `app.state.limiter.allow(...)` 保持，改为 `request.app.state.limiter.allow(...)`
- `get_thread_lock(app, thread_id)` -> `get_thread_lock(request.app, thread_id)`
- 依赖 `get_current_user` / `get_services` 从 `agentlab.api.deps` import
- schema 从 `agentlab.api.rag_agent.schemas` import
- `_chat_events` 等从 `agentlab.api.rag_agent.sse` import
- `_refusal_events` 从 `agentlab.api.streaming` import

- [ ] **Step 5: 更新 `app.py`**

删除四个 chat handler 及其不再使用的 import；import `router as rag_agent_router` 并在 `create_app` 内 `app.include_router(rag_agent_router)`。保留 `from agentlab.api.rag_agent.services import build_services`（lifespan 与测试 patch 目标需要）。在 `create_app` 中补 `app.state.request_timeout = REQUEST_TIMEOUT`，供路由读取。

Run: `uv run pytest -q`
Expected: `430 passed, 27 skipped`。

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(api): move RAG routes, services, schemas into api/rag_agent

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 4: 拆分 Analytics API 子包

**Files:**
- Create: `agentlab/api/analytics/__init__.py`、`services.py`、`events.py`、`schemas.py`、`routes.py`
- Move: `agentlab/api/analytics.py` → 拆分到 `agentlab/api/analytics/{services,events}.py`
- Modify: `agentlab/api/app.py`、`agentlab/api/schemas.py`（最终删除）、`agentlab/api/deps.py`
- Test: `tests/test_analytics_api.py`、`tests/test_analytics_failure.py`

**Interfaces:**
- Produces: `agentlab.api.analytics.routes.router`（三个 `/analytics/*` 端点）、`agentlab.api.analytics.services.AnalyticsServices/build_analytics_services`、`agentlab.api.analytics.events.analytics_events`、`agentlab.api.analytics.schemas.AnalyticsChatRequest/AnalyticsChatResponse/AnalyticsCancelRequest/AnalyticsCancelResponse`。
- Consumes: `agentlab.api.deps`、`agentlab.api.streaming`、`agentlab.api.redaction`、`agentlab.analytics.*`。

- [ ] **Step 1: 更新测试 import 与 patch 目标，确认失败**

`tests/test_analytics_api.py`：

```python
from agentlab.api.analytics.services import AnalyticsServices
```

fixture 改为：

```python
monkeypatch.setattr(
    "agentlab.api.analytics.events.write_audit", noop, raising=False
)
```

`tests/test_analytics_failure.py`：

```python
from agentlab.api.analytics import events
...
await events.analytics_events(...)
monkeypatch.setattr(events, "write_audit", noop)
```

Run: `uv run pytest tests/test_analytics_api.py tests/test_analytics_failure.py -q`
Expected: FAIL，`ModuleNotFoundError: No module named 'agentlab.api.analytics.services'`。

- [ ] **Step 2: 拆分 services/events**

```bash
mkdir -p agentlab/api/analytics
git mv agentlab/api/analytics.py agentlab/api/analytics/services.py
touch agentlab/api/analytics/__init__.py
```

从 `services.py` 拆出 `DEFAULT_STEPS`、`analytics_events`、`_step_summary`、`_audit_stream` 到 `events.py`；`services.py` 只保留 `AnalyticsServices`、`build_analytics_services`。`events.py` 从 `agentlab.api.streaming` import `sse`，从 `agentlab.api.redaction` import `redact_value`。

- [ ] **Step 3: 拆 analytics schemas 并删除 `api/schemas.py`**

把 `agentlab/api/schemas.py` 的 `AnalyticsChatRequest`、`AnalyticsChatResponse`、`AnalyticsCancelRequest`、`AnalyticsCancelResponse` 移到 `agentlab/api/analytics/schemas.py`。确认 `api/schemas.py` 已空后删除。

- [ ] **Step 4: 创建 `routes.py`**

把 `agentlab/api/app.py` 中 `/analytics/chat`、`/analytics/chat/stream`、`/analytics/cancel` 以及 `_analytics_response` 搬入 `agentlab/api/analytics/routes.py`，放在 `router = APIRouter()` 上。替换规则同 Task 3：

- `app.state.limiter` / `.request_timeout` / `.analytics_tasks` -> `request.app.state.*`
- `get_current_user` / `get_analytics_services` 从 `agentlab.api.deps` import
- `_refusal_events` 从 `agentlab.api.streaming` import
- `redact_value` 从 `agentlab.api.redaction` import
- `AnalyticsServices` 从 `agentlab.api.analytics.services` import
- `analytics_events` 从 `agentlab.api.analytics.events` import
- schemas 从 `agentlab.api.analytics.schemas` import

- [ ] **Step 5: 更新 `app.py` 与 `deps.py`**

`app.py` 删除三个 analytics handler 和 `_analytics_response`；import `router as analytics_router` 并 `app.include_router(analytics_router)`；保留 `from agentlab.api.analytics.services import build_analytics_services`（lifespan 与测试 patch 目标需要）。`deps.py` 的 `AnalyticsServices` import 改为 `agentlab.api.analytics.services`。

Run: `uv run pytest -q`
Expected: `430 passed, 27 skipped`。

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(api): move analytics routes and services into api/analytics

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 5: 重命名静态页并收尾组装根

**Files:**
- Move: `agentlab/api/static/index.html` → `agentlab/api/static/rag_agent.html`
- Modify: `agentlab/api/app.py`
- Test: `tests/test_package_layout.py`

- [ ] **Step 1: 更新静态页测试，确认失败**

```python
def test_static_index_exists():
    import agentlab.api.app as app_module

    assert (Path(app_module.STATIC_DIR) / "rag_agent.html").is_file()
```

Run: `uv run pytest tests/test_package_layout.py::test_static_index_exists -q`
Expected: FAIL。

- [ ] **Step 2: 移动页面并更新路由**

```bash
git mv agentlab/api/static/index.html agentlab/api/static/rag_agent.html
```

`app.py` 的 `/` 路由改为 `FileResponse(STATIC_DIR / "rag_agent.html")`。

- [ ] **Step 3: 全量测试**

Run: `uv run pytest -q`
Expected: `430 passed, 27 skipped`。

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor(api): rename index page to rag_agent.html

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 6: 添加旧路径结构守卫测试

**Files:**
- Test: `tests/test_package_layout.py`

**Interfaces:**
- Produces: `test_no_legacy_moved_imports`，扫描 `.py` 中的旧模块 import。

- [ ] **Step 1: 写守卫测试**

在 `tests/test_package_layout.py` 增加：

```python
_MOVED_MODULES = (
    "agentlab.agent",
    "agentlab.rag",
    "agentlab.tools",
    "agentlab.mcp",
    "agentlab.cli",
    "agentlab.api.sse",
    "agentlab.api.services",
    "agentlab.api.schemas",
)


def _moved_import_offenders(root: Path) -> list[str]:
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        if any(part in {".venv", ".git", "__pycache__"} for part in path.parts):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                if any(
                    module == moved or module.startswith(moved + ".")
                    for moved in _MOVED_MODULES
                ):
                    offenders.append(f"{path}: {module}")
    return sorted(set(offenders))


def test_no_legacy_moved_imports():
    assert _moved_import_offenders(PROJECT_ROOT) == []
```

`agentlab.rag_agent.*` 不会被 `agentlab.rag` 误判：判断条件是 `module.startswith("agentlab.rag" + ".")`，而 `agentlab.rag_agent` 在 `rag` 后是 `_` 不是 `.`。

- [ ] **Step 2: 运行并修复残留**

Run: `uv run pytest tests/test_package_layout.py::test_no_legacy_moved_imports -q`
Expected: PASS。若 FAIL，按报告的文件补 import。

- [ ] **Step 3: 全量测试**

Run: `uv run pytest -q`
Expected: `431 passed, 27 skipped`（458 collected）。

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "test: guard against legacy moved module imports

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 7: 更新文档、脚本与最终验证

**Files:**
- Modify: `README.md`、`docs/mcp-clients.md`、`docs/interview-notes.md`、`docs/CHANGELOG.md`、`scripts/demo.sh`
- Test: `tests/test_package_layout.py`（扩展现有守卫测试）

- [ ] **Step 1: 更新文档与脚本**

- `README.md`：替换目录树；把所有 `agentlab/agent/`、`agentlab/rag/`、`agentlab/tools/`、`agentlab/mcp/`、`agentlab/cli.py`、`agentlab/api/static/index.html` 路径改为新路径；MCP 命令改为 `python -m agentlab.rag_agent.mcp.*`；测试数改为 `431 passed / 27 skipped（458 collected）`；把“RAG 是 Analytics API 的基础设施来源”改为“两条线共享 auth/streaming/guard/tracing 模块”。
- `docs/mcp-clients.md`：`python -m agentlab.mcp.*` -> `python -m agentlab.rag_agent.mcp.*`。
- `docs/interview-notes.md`：RAG 线代码入口路径。
- `docs/CHANGELOG.md`：新增 2026-11-26 条目“包结构分层”。
- `scripts/demo.sh`：`python -m agentlab.rag.ingest` -> `python -m agentlab.rag_agent.rag.ingest`；`python -m agentlab.mcp.client` -> `python -m agentlab.rag_agent.mcp.client`；打印的 MCP 命令同步。

- [ ] **Step 2: 扩展守卫测试覆盖脚本与主文档**

把下面的文本检查追加到 `test_no_legacy_moved_imports` 函数体末尾（不新增测试函数，保持 431）：

```python
    checks = {
        Path("scripts/demo.sh"): ("agentlab.rag.ingest", "agentlab.mcp."),
        Path("README.md"): (
            "agentlab/agent/",
            "agentlab/rag/",
            "agentlab/tools/",
            "agentlab/mcp/",
            "agentlab/cli.py",
            "agentlab/api/static/index.html",
        ),
        Path("docs/mcp-clients.md"): ("agentlab.mcp.",),
    }
    offenders = []
    for path, needles in checks.items():
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle in text:
                offenders.append(f"{path}: {needle}")
    assert offenders == []
```

- [ ] **Step 3: 全量测试**

Run: `uv run pytest -q`
Expected: `431 passed, 27 skipped`（458 collected）。

- [ ] **Step 4: 最终验证**

```bash
uv run python -m compileall -q agentlab eval tests
uv run python -c "import agentlab.api.app, agentlab.rag_agent.cli, agentlab.rag_agent.graph, agentlab.rag_agent.mcp.client"
grep -rn "agentlab\.agent\|agentlab\.rag\.\|agentlab\.tools\|agentlab\.mcp\|agentlab\.cli\|agentlab\.api\.sse\|agentlab\.api\.services\|agentlab\.api\.schemas" agentlab eval tests scripts
```

Expected：compileall 与 import 无输出；grep 无命中（`agentlab.rag_agent.*`、`agentlab.api.rag_agent.*` 除外）。

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "docs: update paths for rag_agent package

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Self-Review

- **Spec coverage**：设计文档的领域包迁移、API 拆分、共享模块、入口、测试、脚本、文档、验证均有对应 Task。
- **Step scan**：每个 Task 都有失败测试/验证、实现、全量测试、commit；没有 TBD。
- **Type consistency**：`sse`、`redact_value`、`Services`、`AnalyticsServices`、`router` 的命名在各 Task 的 Interfaces 中一致。
- **Review Focus**：五个高风险失败模式都落到具体测试或验证步骤。
- **Proportion**：计划以移动/import/测试为主，没有转录整个实现。
