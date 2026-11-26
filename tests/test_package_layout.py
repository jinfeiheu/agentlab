"""结构测试：包布局、路径解析与旧导入残留。"""

import ast
from pathlib import Path

from agentlab.config import (
    DOCS_DIR,
    GOLDEN_PATH,
    HARD_DOCS_DIR,
    HARD_GOLDEN_PATH,
    PROJECT_ROOT,
)

_LEGACY_MODULES = frozenset(
    {
        "config",
        "models",
        "auth",
        "security",
        "tickets",
        "memory",
        "context",
        "graph",
        "multi_agent",
        "rag",
        "retrieval",
        "ingest",
        "tools",
        "metrics",
        "tracing",
        "mcp_server",
        "mcp_utils_server",
        "mcp_client",
        "main",
        "api",
    }
)


def _legacy_import_offenders(root: Path) -> list[str]:
    """用 AST 扫描任意缩进层级的旧模块导入。"""
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
            if any(
                module.split(".", 1)[0] in _LEGACY_MODULES
                for module in modules
            ):
                offenders.append(str(path))
                break
    return sorted(set(offenders))


def test_core_modules_import_under_package():
    from agentlab.rag_agent.context import estimate_tokens
    from agentlab.rag_agent.graph import build_graph
    from agentlab.rag_agent.memory import MemoryItem
    from agentlab.rag_agent.multi_agent import build_multi_agent_graph
    from agentlab.models import build_chat_model
    from agentlab.observability.metrics import MetricsRecorder
    from agentlab.observability.tracing import span
    from agentlab.rag_agent.rag.ingest import build_vector_store
    from agentlab.rag_agent.rag.loaders import load_documents
    from agentlab.rag_agent.rag.retrieval import rrf_fuse
    from agentlab.security.auth import UserContext
    from agentlab.security.guard import redact_pii
    from agentlab.rag_agent.tools.builtin import calculator
    from agentlab.rag_agent.tools.tickets import get_ticket

    assert callable(build_graph)
    assert calculator.name == "calculator"
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


def test_legacy_import_guard_catches_indented_import(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def f():\n    from config import X\n", encoding="utf-8"
    )
    assert _legacy_import_offenders(tmp_path) == [str(sample)]


def test_no_legacy_root_imports():
    assert _legacy_import_offenders(PROJECT_ROOT) == []


def test_entrypoint_modules_import():
    import agentlab.rag_agent.cli
    import agentlab.api.app
    import agentlab.rag_agent.mcp.client
    import agentlab.rag_agent.mcp.knowledge_server
    import agentlab.rag_agent.mcp.utils_server

    assert callable(agentlab.rag_agent.cli.main)
    assert callable(agentlab.api.app.serve)
    assert agentlab.api.app.app is not None


def test_console_scripts_declared():
    import tomllib

    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    scripts = data["project"]["scripts"]
    assert scripts["agentlab"] == "agentlab.rag_agent.cli:main"
    assert scripts["agentlab-rag"] == "agentlab.rag_agent.cli:main"
    assert scripts["agentlab-api"] == "agentlab.api.app:serve"
    assert scripts["agentlab-mcp-knowledge"] == "agentlab.rag_agent.mcp.knowledge_server:main"
    assert scripts["agentlab-mcp-utils"] == "agentlab.rag_agent.mcp.utils_server:main"


def test_static_index_exists():
    import agentlab.api.app as app_module

    assert (Path(app_module.STATIC_DIR) / "rag_agent.html").is_file()


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
