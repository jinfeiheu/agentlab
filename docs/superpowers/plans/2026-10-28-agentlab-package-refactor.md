# AgentLab 包结构重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把平铺在根目录的 18 个 Python 模块迁入 `agentlab/` 包并提供包入口；随后把 992 行的 `api.py` 拆成 `api/app.py`、`api/schemas.py`、`api/sse.py`、`api/services.py`，外部行为与现有 259 个离线测试保持不变。

**Architecture:** 两步走。第一步只做机械迁移与入口改造：模块按职责进入 `agent/`、`rag/`、`tools/`、`security/`、`mcp/`、`observability/`、`api/` 子包；`eval/`、`tests/`、`data/`、`scripts/`、`docs/` 保留顶层。第二步在测试保护下拆分 API 层。全程使用绝对导入 `agentlab.*`，不改变业务语义。

**Tech Stack:** Python 3.12、uv、LangChain 1.4、LangGraph 1.2、FastAPI、pytest、Hatchling（构建后端）。

**Spec:** 本计划“目标结构”一节（2026-10-28 与用户确认）；行为基线是现有 `docs/superpowers/specs/2026-10-21-agent-interview-lab-design.md` 与 259 个通过的离线测试。

## Global Constraints

- Python `>=3.10`，实际 3.12；依赖继续由 `uv` 管理，不升级版本。
- 行为不变：重构前 `uv run pytest -q` 为 `259 passed, 7 skipped`；重构后除新增结构测试外，不修改任何断言语义。
- 所有用户可见文字、注释保持中文。
- 包名固定 `agentlab`；包内一律使用绝对导入 `agentlab.*`，不混用相对导入。
- `eval/`、`tests/`、`data/`、`scripts/`、`docs/` 保留在仓库顶层。
- 不自动 `git commit`；文件迁移用 `git mv` 或 `mv`，提交由用户决定。
- 旧命令 `uv run python main.py`、`uvicorn api:app` 不再保留；README、`scripts/demo.sh`、Dockerfile 全部更新。
- 删除范围仅限 `.gitignore` 内的缓存和旧评测结果；2026-10-20 的旧计划/规格移入 `docs/archive/`，不删除。
- 每次任务结束必须跑完整 `uv run pytest -q`，失败不得进入下一任务。

## 目标结构

```text
langchain-demo/
├── agentlab/
│   ├── __init__.py
│   ├── __main__.py              # python -m agentlab
│   ├── cli.py                   # 原 main.py
│   ├── config.py
│   ├── models.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py               # FastAPI 路由/依赖/启动
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   ├── services.py          # 服务构建、并发状态修复、自动记忆 hooks
│   │   ├── sse.py               # SSE 事件、文本/来源提取、流式生成器
│   │   └── static/index.html
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py
│   │   ├── multi_agent.py
│   │   ├── context.py
│   │   └── memory.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── loaders.py           # 原 rag.py
│   │   ├── retrieval.py
│   │   └── ingest.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── builtin.py           # 原 tools.py
│   │   └── tickets.py
│   ├── security/
│   │   ├── __init__.py
│   │   ├── auth.py              # 原 auth.py
│   │   └── guard.py             # 原 security.py
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── client.py            # 原 mcp_client.py
│   │   ├── knowledge_server.py  # 原 mcp_server.py
│   │   └── utils_server.py      # 原 mcp_utils_server.py
│   └── observability/
│       ├── __init__.py
│       ├── tracing.py
│       └── metrics.py
├── eval/                        # 保持顶层
├── tests/                       # 保持顶层
├── data/                        # 保持顶层
├── docs/
│   ├── archive/                 # 新增：2026-10-20 旧计划/规格
│   └── results/                 # 新增：精选最终评测摘要（可提交）
├── scripts/                     # 保持顶层
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 导入映射（旧 → 新）

| 旧模块 | 新模块 |
|---|---|
| `config` | `agentlab.config` |
| `models` | `agentlab.models` |
| `auth` | `agentlab.security.auth` |
| `security` | `agentlab.security.guard` |
| `tickets` | `agentlab.tools.tickets` |
| `memory` | `agentlab.agent.memory` |
| `context` | `agentlab.agent.context` |
| `graph` | `agentlab.agent.graph` |
| `multi_agent` | `agentlab.agent.multi_agent` |
| `rag` | `agentlab.rag.loaders` |
| `retrieval` | `agentlab.rag.retrieval` |
| `ingest` | `agentlab.rag.ingest` |
| `tools` | `agentlab.tools.builtin` |
| `metrics` | `agentlab.observability.metrics` |
| `tracing` | `agentlab.observability.tracing` |
| `mcp_server` | `agentlab.mcp.knowledge_server` |
| `mcp_utils_server` | `agentlab.mcp.utils_server` |
| `mcp_client` | `agentlab.mcp.client` |
| `main` | `agentlab.cli` |
| `api` | `agentlab.api.app`（第二步再拆） |

路径常量变化：

- `config.BASE_DIR` → `config.PROJECT_ROOT`（`Path(__file__).resolve().parents[1]`）。
- `DATA_DIR = PROJECT_ROOT / "data"`；`DOCS_DIR = DATA_DIR / "docs"`；`GOLDEN_PATH = PROJECT_ROOT / "eval" / "golden.jsonl"`；hard 路径同理。
- `api.STATIC_DIR = Path(__file__).resolve().parent / "static"`。
- `mcp_client` 的 stdio `cwd` 改用 `PROJECT_ROOT`。

## Review Focus

1. **旧导入残留**：任意 `from config import` / `import api` / `import main` 残留都会造成 ImportError 或悄悄导入错误模块。Task 1 增加 `test_no_legacy_root_imports`，全仓扫描 `.py`。
2. **路径解析**：`config.py` 进入包内后 `BASE_DIR` 语义变化；`data/`、`eval/`、`static/` 可能找不到。Task 1 增加 `test_project_paths_exist`，Task 2 增加 `test_static_index_exists`。
3. **入口与子进程**：MCP stdio 配置、Dockerfile CMD、`scripts/demo.sh`、README 命令仍指向旧文件。Task 2 增加入口导入测试，并逐项更新后跑 `grep` 验证。
4. **API 拆分后的 monkeypatch 目标**：测试 patch 的 `REQUEST_TIMEOUT`、`ENABLE_AUTO_MEMORY`、`build_services`、`USE_DB` 等常量会随函数搬家。Task 4/5 更新测试模块路径，并保留原有断言语义。
5. **Docker 构建缺包源码**：新增 Hatchling 后，Dockerfile 若仍只 `COPY pyproject.toml uv.lock` 就 `uv sync`，会因找不到 `agentlab/` 构建失败。Task 2 必须改成“先装依赖、再复制源码、再安装项目”，并验证 `docker build`。

---

# Phase 1：包迁移

### Task 1: 迁移核心模块到 `agentlab/` 包

**Files:**
- Create: `agentlab/__init__.py`、`agentlab/agent/__init__.py`、`agentlab/rag/__init__.py`、`agentlab/tools/__init__.py`、`agentlab/security/__init__.py`、`agentlab/observability/__init__.py`、`agentlab/api/__init__.py`
- Move: `config.py`、`models.py`、`auth.py`、`security.py`、`tickets.py`、`memory.py`、`context.py`、`graph.py`、`multi_agent.py`、`rag.py`、`retrieval.py`、`ingest.py`、`tools.py`、`metrics.py`、`tracing.py`（按映射表）
- Modify: 上述模块的 import；根目录 `main.py`、`api.py`、`mcp_server.py`、`mcp_utils_server.py`、`mcp_client.py` 的 import；`eval/*.py`、`tests/*.py` 的 import
- Test: `tests/test_package_layout.py`

**Interfaces:**
- Consumes: 无（第一步）。
- Produces: `agentlab.config` 暴露 `PROJECT_ROOT`、`DATA_DIR`、`DOCS_DIR`、`GOLDEN_PATH`、`HARD_DOCS_DIR`、`HARD_GOLDEN_PATH` 及其余原有常量；其余模块保持原公开函数/类名不变，只改导入路径。

- [ ] **Step 1: 写失败的结构测试**

```python
# tests/test_package_layout.py
import re
from pathlib import Path

from agentlab.config import (
    DOCS_DIR,
    GOLDEN_PATH,
    HARD_DOCS_DIR,
    HARD_GOLDEN_PATH,
    PROJECT_ROOT,
)


def test_core_modules_import_under_package():
    from agentlab.agent.context import estimate_tokens
    from agentlab.agent.graph import build_graph
    from agentlab.agent.memory import MemoryItem
    from agentlab.agent.multi_agent import build_multi_agent_graph
    from agentlab.models import build_chat_model
    from agentlab.observability.metrics import MetricsRecorder
    from agentlab.observability.tracing import span
    from agentlab.rag.ingest import build_vector_store
    from agentlab.rag.loaders import load_documents
    from agentlab.rag.retrieval import rrf_fuse
    from agentlab.security.auth import UserContext
    from agentlab.security.guard import redact_pii
    from agentlab.tools.builtin import calculator
    from agentlab.tools.tickets import get_ticket

    assert callable(build_graph)
    assert callable(calculator)
    assert callable(redact_pii)
    assert UserContext(user_id="u").user_id == "u"
    assert MemoryItem(type="fact", key="fact.x", value="v").value == "v"
    assert callable(estimate_tokens)
    assert callable(load_documents)
    assert callable(rrf_fuse)
    assert callable(build_vector_store)
    assert callable(build_multi_agent_graph)
    assert callable(build_chat_model)
    assert MetricsRecorder().summary()["count"] == 0
    assert callable(span)
    assert get_ticket.name == "get_ticket"


def test_project_paths_exist():
    assert (PROJECT_ROOT / "pyproject.toml").is_file()
    assert DOCS_DIR.is_dir()
    assert GOLDEN_PATH.is_file()
    assert HARD_DOCS_DIR.is_dir()
    assert HARD_GOLDEN_PATH.is_file()


def test_no_legacy_root_imports():
    pattern = re.compile(
        r"^(?:from|import) (?:config|models|auth|security|tickets|memory|context|"
        r"graph|multi_agent|rag|retrieval|ingest|tools|metrics|tracing)"
        r"(?:\s|$|\.)",
        re.MULTILINE,
    )
    offenders = []
    for path in Path(".").rglob("*.py"):
        if any(part in {".venv", ".git", "__pycache__"} for part in path.parts):
            continue
        if pattern.search(path.read_text(encoding="utf-8")):
            offenders.append(str(path))
    assert offenders == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest -q tests/test_package_layout.py`
Expected: FAIL，`ModuleNotFoundError: No module named 'agentlab'`

- [ ] **Step 3: 创建包骨架**

```bash
mkdir -p agentlab/{agent,rag,tools,security,observability,api,mcp}
```

为 `agentlab/` 及每个子包创建 `__init__.py`，内容为一句话中文 docstring（例如 `"""AgentLab 核心包。"""`）。

- [ ] **Step 4: 用 `git mv` 迁移核心模块**

```bash
git mv config.py agentlab/config.py
git mv models.py agentlab/models.py
git mv auth.py agentlab/security/auth.py
git mv security.py agentlab/security/guard.py
git mv tickets.py agentlab/tools/tickets.py
git mv memory.py agentlab/agent/memory.py
git mv context.py agentlab/agent/context.py
git mv graph.py agentlab/agent/graph.py
git mv multi_agent.py agentlab/agent/multi_agent.py
git mv rag.py agentlab/rag/loaders.py
git mv retrieval.py agentlab/rag/retrieval.py
git mv ingest.py agentlab/rag/ingest.py
git mv tools.py agentlab/tools/builtin.py
git mv metrics.py agentlab/observability/metrics.py
git mv tracing.py agentlab/observability/tracing.py
```

本任务暂不移动 `main.py`、`api.py`、`mcp_*.py`、`static/`，它们留在根目录，只更新 import。

- [ ] **Step 5: 更新 `agentlab/config.py` 的路径常量**

把原来的 `BASE_DIR = Path(__file__).resolve().parent` 改为：

```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = DATA_DIR / "docs"
GOLDEN_PATH = PROJECT_ROOT / "eval" / "golden.jsonl"
HARD_DOCS_DIR = Path(
    os.getenv("HARD_DOCS_DIR", str(DATA_DIR / "docs_hard"))
)
HARD_GOLDEN_PATH = Path(
    os.getenv("HARD_GOLDEN_PATH", str(PROJECT_ROOT / "eval" / "golden_hard.jsonl"))
)
```

删除 `BASE_DIR` 的旧定义；若仍有引用，全部改为 `PROJECT_ROOT`。

- [ ] **Step 6: 更新已迁移模块的内部 import**

按导入映射表把每个文件里的旧模块名改成 `agentlab.*`，包括函数内的延迟 import（例如 `agentlab/rag/retrieval.py` 的 `build_pgvector_hybrid_retriever`）。例如：

```python
# agentlab/tools/builtin.py
from agentlab.observability.tracing import span
from agentlab.rag.loaders import format_docs
```

```python
# agentlab/agent/graph.py
from agentlab.agent.context import ...
from agentlab.agent.memory import load_profile, save_episode
from agentlab.config import CONTEXT_MAX_TOKENS, ENABLE_AUTO_MEMORY
from agentlab.security.auth import UserContext
from agentlab.security.guard import ...
```

`agentlab/rag/retrieval.py` 里的函数内延迟 import 也要改，例如 `from agentlab.config import ...`。

- [ ] **Step 7: 更新根目录入口文件的 import（暂不移动）**

`main.py`、`api.py`、`mcp_server.py`、`mcp_utils_server.py`、`mcp_client.py` 全部改指向 `agentlab.*`；`api.py` 的 `STATIC_DIR` 暂时改为 `PROJECT_ROOT / "static"`，`mcp_client.py` 的 `BASE_DIR` 改为 `PROJECT_ROOT`。

- [ ] **Step 8: 更新 `eval/` 的 import**

`eval/judge.py`、`eval/run_eval.py`、`eval/text_metrics.py` 改指向 `agentlab.*`；`eval/text_metrics.py` 的 `from retrieval import tokenize` 改为 `from agentlab.rag.retrieval import tokenize`。

- [ ] **Step 9: 更新 `tests/` 的 import**

按映射表更新所有测试文件；本任务保留 `import api`、`import main`、`from mcp_client import ...`（这些入口文件仍在根目录）。`tests/fakes.py` 的 `from auth import sign_token` 改为 `from agentlab.security.auth import sign_token`。

- [ ] **Step 10: 运行完整测试**

Run: `uv run pytest -q`
Expected: `262 passed, 7 skipped`（原 259 + 新增结构测试 3）

- [ ] **Step 11: 扫描旧导入**

Run:

```bash
grep -rnE "^(from|import) (config|models|auth|security|tickets|memory|context|graph|multi_agent|rag|retrieval|ingest|tools|metrics|tracing)([[:space:]]|$|\.)" --include="*.py" . | grep -v "/.venv/"
```

Expected: 无输出。入口文件 `main.py`、`api.py`、`mcp_*.py` 仍允许以旧名被测试导入。

---

### Task 2: 迁移入口、打包配置与一键命令

**Files:**
- Move: `main.py` → `agentlab/cli.py`；`api.py` → `agentlab/api/app.py`；`mcp_server.py` → `agentlab/mcp/knowledge_server.py`；`mcp_utils_server.py` → `agentlab/mcp/utils_server.py`；`mcp_client.py` → `agentlab/mcp/client.py`；`static/index.html` → `agentlab/api/static/index.html`
- Create: `agentlab/__main__.py`、`agentlab/api/static/`（目录）
- Modify: `agentlab/api/app.py`（`STATIC_DIR`、`serve()`）、`agentlab/mcp/client.py`（stdio 配置）、`pyproject.toml`、`Dockerfile`、`scripts/demo.sh`、`README.md`、`docs/mcp-clients.md`
- Modify tests: `tests/test_main.py`、`tests/test_api.py`、`tests/test_mcp.py`、`tests/test_mcp_multi.py`、`tests/fakes.py`、`tests/test_persistence.py`
- Test: `tests/test_package_layout.py`

**Interfaces:**
- Consumes: Task 1 的 `agentlab.*` 模块。
- Produces: console scripts `agentlab`、`agentlab-api`、`agentlab-mcp-knowledge`、`agentlab-mcp-utils`；`python -m agentlab` 等价于 CLI；`agentlab.api.app:app` 是 ASGI 入口；MCP stdio 命令为 `sys.executable -m agentlab.mcp.knowledge_server` 与 `sys.executable -m agentlab.mcp.utils_server`。

- [ ] **Step 1: 扩展结构测试**

在 `tests/test_package_layout.py` 增加：

```python
def test_entrypoint_modules_import():
    import agentlab.cli
    import agentlab.api.app
    import agentlab.mcp.client
    import agentlab.mcp.knowledge_server
    import agentlab.mcp.utils_server

    assert callable(agentlab.cli.main)
    assert callable(agentlab.api.app.serve)
    assert agentlab.api.app.app is not None


def test_console_scripts_declared():
    import tomllib
    from pathlib import Path

    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    scripts = data["project"]["scripts"]
    assert scripts["agentlab"] == "agentlab.cli:main"
    assert scripts["agentlab-api"] == "agentlab.api.app:serve"
    assert scripts["agentlab-mcp-knowledge"] == "agentlab.mcp.knowledge_server:main"
    assert scripts["agentlab-mcp-utils"] == "agentlab.mcp.utils_server:main"


def test_static_index_exists():
    from pathlib import Path
    import agentlab.api.app as app_module

    assert (Path(app_module.STATIC_DIR) / "index.html").is_file()
```

同时把 Task 1 的 `test_no_legacy_root_imports` 正则扩展到入口模块：`mcp_server|mcp_utils_server|mcp_client|main|api`。这样本任务完成后，旧入口 import 必须全部消失。

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest -q tests/test_package_layout.py`
Expected: FAIL，`agentlab.cli` / `agentlab.api.app` 不存在。

- [ ] **Step 3: 移动入口文件与静态页**

```bash
git mv main.py agentlab/cli.py
git mv api.py agentlab/api/app.py
git mv mcp_server.py agentlab/mcp/knowledge_server.py
git mv mcp_utils_server.py agentlab/mcp/utils_server.py
git mv mcp_client.py agentlab/mcp/client.py
mkdir -p agentlab/api/static
git mv static/index.html agentlab/api/static/index.html
rmdir static
```

- [ ] **Step 4: 更新移动后文件的 import 与路径**

- `agentlab/cli.py`：所有 `from config/auth/graph/...` 改为 `from agentlab.*`；`if __name__ == "__main__": main()` 保留。
- `agentlab/api/app.py`：所有 import 改为 `agentlab.*`；`STATIC_DIR = Path(__file__).resolve().parent / "static"`；删除 `BASE_DIR` 引用；文件底部保留 `app = create_app()`，并新增：

```python
def serve() -> None:
    """用 uvicorn 启动 API；console script `agentlab-api` 的入口。"""
    import uvicorn

    uvicorn.run("agentlab.api.app:app", host="0.0.0.0", port=8000)
```

- `agentlab/mcp/client.py`：新增 `import sys`；`from agentlab.config import PROJECT_ROOT, ...`；stdio 配置改为：

```python
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
```

- `agentlab/mcp/knowledge_server.py`、`agentlab/mcp/utils_server.py`：import 改为 `agentlab.*`；保留 `main()` 与 `if __name__ == "__main__": main()`。
- 新增 `agentlab/__main__.py`：

```python
"""支持 `python -m agentlab`。"""

from agentlab.cli import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: 更新 `pyproject.toml`**

在文件顶部加入：

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

在 `[project]` 后加入：

```toml
[project.scripts]
agentlab = "agentlab.cli:main"
agentlab-api = "agentlab.api.app:serve"
agentlab-mcp-knowledge = "agentlab.mcp.knowledge_server:main"
agentlab-mcp-utils = "agentlab.mcp.utils_server:main"
```

加入 Hatchling 包发现配置：

```toml
[tool.hatch.build.targets.wheel]
packages = ["agentlab"]
```

保留现有 `[tool.pytest.ini_options]` 的 `pythonpath = ["."]`。

- [ ] **Step 6: 更新测试入口引用**

- `tests/test_main.py`：`import main` → `from agentlab import cli as main`。
- `tests/test_api.py`：`import api` → `import agentlab.api.app as api`；`from api import create_app` → `from agentlab.api.app import create_app`；`from auth import ...` → `from agentlab.security.auth import ...`。
- `tests/fakes.py`：`from api import create_app` → `from agentlab.api.app import create_app`；`from auth import sign_token` → `from agentlab.security.auth import sign_token`。
- `tests/test_mcp.py`：`from mcp_client import ...` → `from agentlab.mcp.client import ...`；断言改为 `"agentlab.mcp.knowledge_server" in " ".join(...)`、`"agentlab.mcp.utils_server" in ...`。
- `tests/test_mcp_multi.py`：`import mcp_client` → `import agentlab.mcp.client as mcp_client`；断言同步更新。
- `tests/test_persistence.py`：`import config` → `import agentlab.config as config`；`from graph import build_graph` → `from agentlab.agent.graph import build_graph`；`from tools import calculator` → `from agentlab.tools.builtin import calculator`；函数内的 `import api` → `import agentlab.api.app as api`（Task 4 再改成 `agentlab.api.services`）。

- [ ] **Step 7: 更新 Dockerfile**

把原来的“复制 pyproject + uv.lock → uv sync → COPY . .”改成两阶段安装，确保 Hatchling 能读到包源码：

```dockerfile
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project \
    --group serve --group observability --group rag --group mcp

COPY . .
RUN uv sync --frozen --no-dev \
    --group serve --group observability --group rag --group mcp
```

把 CMD 改为：

```dockerfile
CMD ["uv", "run", "--no-sync", "agentlab-api"]
```

- [ ] **Step 8: 更新 `scripts/demo.sh` 与 `docs/mcp-clients.md`**

- `uv run python main.py` → `uv run agentlab`（保留 `--simple` / `--multi --user alice` 参数）。
- `uvicorn api:app` → `uvicorn agentlab.api.app:app`；如果脚本只想一条命令，可用 `uv run agentlab-api`。
- `uv run python mcp_server.py ...` → `uv run python -m agentlab.mcp.knowledge_server ...`。
- `uv run python mcp_utils_server.py ...` → `uv run python -m agentlab.mcp.utils_server ...`。
- `docs/mcp-clients.md` 中的 stdio 命令同步更新。

- [ ] **Step 9: 更新 README**

更新目录树、快速开始、API、Phoenix、MCP、多 Agent、评测复现命令中的旧路径；同步更新各阶段“代码入口”里的文件路径。新增：

```bash
uv run agentlab                 # CLI 默认手写图
uv run agentlab --simple        # create_agent 封装
uv run agentlab --multi --user alice
uv run agentlab-api             # API 一条命令启动
```

- [ ] **Step 10: 同步 lock 与安装**

Run:

```bash
uv lock
uv sync --all-groups
```

Expected: 成功；`uv run python -c "import importlib.metadata as m; print(sorted(e.name for e in m.entry_points(group='console_scripts') if e.name.startswith('agentlab')))"` 输出四个 console script。

- [ ] **Step 11: 运行完整测试**

Run: `uv run pytest -q`
Expected: `265 passed, 7 skipped`（Task 1 的 3 个 + 本任务 3 个）

- [ ] **Step 12: 验证入口与 Docker 构建**

Run:

```bash
uv run python -c "import agentlab.cli, agentlab.api.app, agentlab.mcp.client"
uv run python -m eval.run_eval --help
grep -rnE "^(from|import) (config|models|auth|security|tickets|memory|context|graph|multi_agent|rag|retrieval|ingest|tools|metrics|tracing|mcp_server|mcp_utils_server|mcp_client|main|api)([[:space:]]|$|\.)" --include="*.py" . | grep -v "/.venv/"
grep -rn "python main.py\|api:app\|mcp_server.py\|mcp_utils_server.py" README.md scripts docs/mcp-clients.md docs/interview-notes.md Dockerfile docker-compose.yml
docker build -t agentlab-refactor-check .
```

Expected: 导入与 `--help` 无异常；两条 grep 无输出；Docker 构建成功（若本机 Docker 不可用，记录“未验证”，不要跳过说明）。

---

### Task 3: 清理、归档与评测证据整理

**Files:**
- Delete: `.pytest_cache/`、`__pycache__/`、`eval/__pycache__/`、`tests/__pycache__/`、`agentlab/**/__pycache__/`
- Delete: `eval/results/` 中未保留的旧结果
- Move: `docs/superpowers/plans/2026-10-20-langchain-demo.md`、`docs/superpowers/specs/2026-10-20-langchain-demo-design.md` → `docs/archive/`
- Create: `docs/results/`（精选最终 `.md` + `README.md`）
- Modify: `README.md`（目录树、测试数、结果说明）

**Interfaces:**
- Consumes: Task 2 的最终目录与测试结果。
- Produces: 干净仓库；`docs/results/` 中的评测摘要可随仓库提交。

- [ ] **Step 1: 删除缓存**

```bash
find . -path ./.venv -prune -o -name "__pycache__" -type d -print -exec rm -rf {} +
rm -rf .pytest_cache
```

- [ ] **Step 2: 删除旧评测结果，保留最终矩阵**

保留以下 13 组 `.json/.md`（共 26 个文件）：

```text
easy-baseline-deepseek
easy-baseline-qwen35-4b
easy-hybrid-deepseek
easy-hybrid-qwen35-4b
easy-hybrid-rerank-deepseek
easy-hybrid-rerank-qwen35-4b
hard-baseline-deepseek
hard-baseline-qwen35-4b
hard-hybrid-deepseek
hard-hybrid-qwen35-4b
hard-hybrid-rerank-deepseek
hard-hybrid-rerank-qwen35-4b
hard-closed-book
```

删除其余文件：`baseline.*`、`hybrid-model-rerank.*`、`hybrid-rerank.*`、`smoke*.*`、`hard-smoke*.*`、`hard-baseline-qwen3-8b-extra.*`。

- [ ] **Step 3: 归档 2026-10-20 旧计划与规格**

```bash
mkdir -p docs/archive
git mv docs/superpowers/plans/2026-10-20-langchain-demo.md docs/archive/
git mv docs/superpowers/specs/2026-10-20-langchain-demo-design.md docs/archive/
```

保留 `docs/superpowers/plans/2026-10-21-agent-interview-lab.md` 和对应 spec。

- [ ] **Step 4: 精选评测摘要到 `docs/results/`**

```bash
mkdir -p docs/results
cp eval/results/easy-*.md docs/results/
cp eval/results/hard-*.md docs/results/
```

新增 `docs/results/README.md`，内容：

```markdown
# 评测结果摘要

这里保存最终评测矩阵的 Markdown 摘要，随仓库提交，方便直接查看。

原始 `.json` 结果在本地 `eval/results/`，被 `.gitignore` 排除，不随仓库提交。
复现命令见主 README 的“评测方法与结果”一节。
```

- [ ] **Step 5: 更新 README**

- 目录树替换为 `agentlab/` 结构，加入 `docs/archive/`、`docs/results/`。
- 把“复现时以 `eval/results/*.json` 为准”改为“摘要见 `docs/results/`，原始 JSON 在本地 `eval/results/`”。
- 把测试数改成 Task 2 实际输出（预计 265）。
- 删除对已删除旧结果的引用（如 `hard-smoke.md` 的固定输出文件描述，保留命令即可）。

- [ ] **Step 6: 最终验证**

```bash
uv run pytest -q
git status --short
grep -rnE "^(from|import) (config|models|auth|security|tickets|memory|context|graph|multi_agent|rag|retrieval|ingest|tools|metrics|tracing|mcp_server|mcp_utils_server|mcp_client|main|api)([[:space:]]|$|\.)" --include="*.py" . | grep -v "/.venv/"
grep -rn "python main.py\|api:app\|mcp_server.py\|mcp_utils_server.py" README.md scripts docs/mcp-clients.md docs/interview-notes.md Dockerfile docker-compose.yml
```

Expected: 测试全绿；旧 import/旧命令无输出；`git status` 只显示预期的移动/新增/删除。

---

# Phase 2：拆分 API 层

### Task 4: 抽出 `schemas.py` 与 `services.py`

**Files:**
- Create: `agentlab/api/schemas.py`、`agentlab/api/services.py`
- Modify: `agentlab/api/app.py`
- Modify tests: `tests/test_api.py`、`tests/test_persistence.py`
- Test: `tests/test_api_modules.py`

**Interfaces:**
- `schemas.py`：`LoginRequest(username: str, password: str)`、`LoginResponse(token: str)`、`ChatRequest(message: str, session_id: str)`、`ResumeRequest(session_id: str, answer: str)`、`ChatResponse(answer: str, sources: list[str], interrupt: dict | None = None)`。
- `services.py`：`Services`（字段 `graph`、`retriever`、`db_check`、`model`、`memory_store`、`_closer` 与 `async aclose()`）、`async build_services() -> Services`、`_needs_db_check() -> bool`、`async _check_db() -> None`。
- `app.py` 保留：`RateLimiter`、`get_current_user`、`get_services`、`get_thread_lock`、`create_app`、`serve`、`app`。

- [ ] **Step 1: 写失败的结构测试**

```python
# tests/test_api_modules.py
def test_schemas_and_services_are_split():
    from agentlab.api.schemas import (
        ChatRequest,
        ChatResponse,
        LoginRequest,
        LoginResponse,
        ResumeRequest,
    )
    from agentlab.api.services import Services, build_services

    assert ChatRequest(message="hi", session_id="s").session_id == "s"
    assert LoginRequest(username="alice", password="p").username == "alice"
    assert LoginResponse(token="t").token == "t"
    assert ResumeRequest(session_id="s", answer="y").answer == "y"
    assert ChatResponse(answer="a", sources=[]).interrupt is None
    assert callable(build_services)
    assert Services(graph=object()).retriever is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest -q tests/test_api_modules.py`
Expected: FAIL，`agentlab.api.schemas` / `agentlab.api.services` 不存在。

- [ ] **Step 3: 创建 `agentlab/api/schemas.py`**

把 `LoginRequest`、`LoginResponse`、`ChatRequest`、`ResumeRequest`、`ChatResponse` 从 `app.py` 原样移入；保留中文 docstring；只 import `pydantic.BaseModel`。

- [ ] **Step 4: 创建 `agentlab/api/services.py`**

移入 `Services`、`_needs_db_check`、`_check_db`、`build_services`；import 相应 `agentlab.*` 模块与 config 常量。`RateLimiter` 留在 `app.py`。

- [ ] **Step 5: 更新 `app.py`**

删除已移出的类/函数；改为：

```python
from agentlab.api.schemas import (
    ChatRequest,
    ChatResponse,
    LoginRequest,
    LoginResponse,
    ResumeRequest,
)
from agentlab.api.services import Services, build_services
```

保留所有路由与 `create_app` 逻辑不变。

- [ ] **Step 6: 更新测试的 patch 目标**

- `tests/test_api.py`：
  - 保留 `import agentlab.api.app as api` 用于 `RATE_LIMIT_PER_MINUTE`、`REQUEST_TIMEOUT`、`build_services`、`setup_tracing` 等 app 级 patch。
  - `_needs_db_check` 改为 `from agentlab.api.services import _needs_db_check`，并 `import agentlab.api.services as services`；把 `monkeypatch.setattr(api, "USE_DB"/"RAG_MODE"/"USE_MCP", ...)` 改为 patch `services`。
- `tests/test_persistence.py`：`import agentlab.api.services as api`，因为它 patch `USE_DB`、`DATABASE_URL`、`build_chat_model`、`build_inmemory_retriever` 并调用 `build_services`。

- [ ] **Step 7: 运行完整测试**

Run: `uv run pytest -q`
Expected: 全绿（预计 266 passed, 7 skipped）。

---

### Task 5: 抽出 `sse.py`，瘦身 `app.py`

**Files:**
- Create: `agentlab/api/sse.py`
- Modify: `agentlab/api/app.py`、`agentlab/api/services.py`
- Modify tests: `tests/test_api.py`
- Test: `tests/test_api_modules.py`

**Interfaces:**
- `sse.py`：`sse(payload) -> str`、`_refusal_events(message)`、`_extract_answer(result) -> str`、`_extract_sources(result) -> list[str]`、`_interrupt_payload(state) -> dict | None`、`async _has_interrupt(graph, config) -> bool`、`async _get_interrupt(graph, config) -> dict | None`、`_tool_events(message) -> list[dict]`、`_chat_events(...)`。
- `services.py` 新增：`_pending_tool_calls(messages) -> tuple[dict[str, str], bool]`、`async _reset_thread(graph, thread_id) -> None`、`async _prepare_thread(graph, config) -> None`、`async _maybe_extract_memory(services, user, text, messages) -> None`、`async _post_turn_memory(graph, config, services, user, user_text) -> None`。
- `app.py` 只保留 HTTP 层：`RateLimiter`、依赖解析、路由、`create_app`、`serve`、`app`。

- [ ] **Step 1: 写失败的结构测试**

在 `tests/test_api_modules.py` 增加：

```python
def test_streaming_and_thread_helpers_are_split():
    from agentlab.api.sse import _chat_events, _tool_events
    from agentlab.api.services import (
        _maybe_extract_memory,
        _pending_tool_calls,
        _post_turn_memory,
        _prepare_thread,
    )

    assert callable(_chat_events)
    assert callable(_tool_events)
    assert callable(_pending_tool_calls)
    assert callable(_prepare_thread)
    assert callable(_maybe_extract_memory)
    assert callable(_post_turn_memory)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest -q tests/test_api_modules.py`
Expected: FAIL，`_chat_events` 等不在目标模块。

- [ ] **Step 3: 创建 `agentlab/api/sse.py`**

移入 `sse`、`_refusal_events`、`_content_text`、`_message_text`、`_extract_answer`、`_sources_from_text`、`_dedupe`、`_extract_sources`、`_interrupt_payload`、`_has_interrupt`、`_get_interrupt`、`_redact_value`、`_tool_events`、`_chat_events` 及常量 `_SOURCE_RE`、`_TOOL_RESULT_CHARS`。

`_chat_events` 通过 import 使用 `services` 里的 `_prepare_thread`、`_post_turn_memory`；不要反向 import `app.py`。

- [ ] **Step 4: 把线程修复与记忆 hooks 移到 `services.py`**

移入 `_pending_tool_calls`、`_reset_thread`、`_prepare_thread`、`_maybe_extract_memory`、`_post_turn_memory`；保留原中文 docstring 与异常处理语义。

- [ ] **Step 5: 更新 `app.py`**

删除已移出的函数；从 `agentlab.api.sse` import `_chat_events`、`_extract_answer`、`_extract_sources`、`_get_interrupt`、`_refusal_events`；从 `agentlab.api.services` import `_maybe_extract_memory`、`_prepare_thread`。路由逻辑不变。

- [ ] **Step 6: 更新 `tests/test_api.py`**

- `api._pending_tool_calls` → `from agentlab.api.services import _pending_tool_calls`。
- `api._chat_events` → `from agentlab.api.sse import _chat_events`。
- `api._tool_events` → `from agentlab.api.sse import _tool_events`。
- `api._maybe_extract_memory` / `api._post_turn_memory` → `from agentlab.api.services import ...`。
- 记忆测试的 `monkeypatch.setattr(api, "ENABLE_AUTO_MEMORY"/"maybe_extract_and_save", ...)` 改为 patch `agentlab.api.services`；`test_chat_triggers_candidate_extraction` 中后续调用的是 services 模块的 globals，必须 patch services。

- [ ] **Step 7: 运行完整测试**

Run: `uv run pytest -q`
Expected: 全绿（预计 267 passed, 7 skipped）。

- [ ] **Step 8: 检查文件规模**

Run:

```bash
wc -l agentlab/api/app.py agentlab/api/schemas.py agentlab/api/services.py agentlab/api/sse.py
```

Expected: `app.py` < 400 行；`schemas.py` < 80 行；`services.py` 与 `sse.py` 各自职责单一（不要求固定行数）。

- [ ] **Step 9: 同步 README 测试数**

把 README 中的测试数改为实际输出（预计 `267 passed, 7 skipped`）。

---

## 最终验收

- [ ] `uv run pytest -q` → 全绿，记录实际 `passed/skipped` 数并同步 README。
- [ ] `uv run python -c "import agentlab, agentlab.cli, agentlab.api.app, agentlab.mcp.client"` → 无异常。
- [ ] `uv run python -m eval.run_eval --help` → 正常输出用法。
- [ ] `grep` 旧 import / 旧命令 → 无输出（`docs/archive/` 除外）。
- [ ] `git status --short` → 只包含预期的移动、新增、删除；不包含 `.env`、`.venv/`、`eval/results/` 原始 JSON。
- [ ] `docker build -t agentlab-refactor-check .` → 成功（若 Docker 不可用，明确记录未验证）。
- [ ] README 目录树、命令、测试数与实际一致。
