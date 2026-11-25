"""集中读取环境变量,避免各模块散落 os.getenv。"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = DATA_DIR / "docs"
GOLDEN_PATH = PROJECT_ROOT / "eval" / "golden.jsonl"
ANALYTICS_GOLDEN_PATH = PROJECT_ROOT / "eval" / "analytics_golden.jsonl"
# hard 评测与 easy 集完全隔离:独立语料、golden 和 pgvector collection。
HARD_DOCS_DIR = Path(
    os.getenv("HARD_DOCS_DIR", str(DATA_DIR / "docs_hard"))
)
HARD_GOLDEN_PATH = Path(
    os.getenv("HARD_GOLDEN_PATH", str(PROJECT_ROOT / "eval" / "golden_hard.jsonl"))
)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agentlab"
)
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")
# 与 bge-m3 的输出维度保持一致;Store 语义索引与文档向量共用该维度。
EMBED_DIMS = int(os.getenv("EMBED_DIMS", "1024"))
AUTH_SECRET = os.getenv("AUTH_SECRET", "dev-only-change-me-please-replace-me")
TRACING_ENABLED = _env_bool("TRACING_ENABLED", False)
PHOENIX_ENDPOINT = os.getenv(
    "PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces"
)
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
RAG_MODE = os.getenv("RAG_MODE", "baseline")
# 专用 cross-encoder reranker 默认开启;LLM rerank 默认关闭。
RERANK_ENABLED = _env_bool("RERANK_ENABLED", True)
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
RERANK_DEVICE = os.getenv("RERANK_DEVICE", "cpu")
LLM_RERANK_ENABLED = _env_bool("LLM_RERANK_ENABLED", False)
USE_DB = _env_bool("USE_DB", False)
USE_MCP = _env_bool("USE_MCP", False)
# MCP 传输:stdio(本地子进程) 或 streamable_http(远程服务)
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")
MCP_AGENTLAB_URL = os.getenv(
    "MCP_AGENTLAB_URL", "http://localhost:8811/mcp"
)
MCP_UTILS_URL = os.getenv("MCP_UTILS_URL", "http://localhost:8812/mcp")
PG_COLLECTION = os.getenv("PG_COLLECTION", "docs")
PG_HARD_COLLECTION = os.getenv("PG_HARD_COLLECTION", "docs_hard")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "60"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
CONTEXT_MAX_TOKENS = int(os.getenv("CONTEXT_MAX_TOKENS", "6000"))
ENABLE_AUTO_MEMORY = _env_bool("ENABLE_AUTO_MEMORY", False)
# 自动 episode 记忆的保留天数;Postgres Store 支持 TTL,InMemoryStore 会忽略。
MEMORY_EPISODE_TTL_DAYS = float(os.getenv("MEMORY_EPISODE_TTL_DAYS", "30"))
# 评测裁判模型:默认 DeepSeek;可设为本地 Ollama 模型做跨模型对照。
EVAL_JUDGE_MODEL = os.getenv("EVAL_JUDGE_MODEL", DEEPSEEK_MODEL)

# 数据分析 Agent:只读连接、查询限制与租户默认值。
ANALYTICS_DATABASE_URL = os.getenv(
    "ANALYTICS_DATABASE_URL",
    "postgresql://analytics_reader:analytics_reader@localhost:5432/agentlab",
)
# seed 需要写权限；只读角色不能用来建表/灌数据。
ANALYTICS_SEED_DATABASE_URL = os.getenv(
    "ANALYTICS_SEED_DATABASE_URL", DATABASE_URL
)
# 审计写入需要写权限；生产应使用独立的 app 写角色。
ANALYTICS_AUDIT_DATABASE_URL = os.getenv(
    "ANALYTICS_AUDIT_DATABASE_URL", DATABASE_URL
)
ANALYTICS_MAX_ROWS = int(os.getenv("ANALYTICS_MAX_ROWS", "200"))
ANALYTICS_STATEMENT_TIMEOUT = int(
    os.getenv("ANALYTICS_STATEMENT_TIMEOUT", "5000")
)
ANALYTICS_MODEL_TIMEOUT = float(
    os.getenv("ANALYTICS_MODEL_TIMEOUT", "30")
)
ANALYTICS_COST_THRESHOLD = float(
    os.getenv("ANALYTICS_COST_THRESHOLD", "100000")
)
ANALYTICS_TENANT_ID = os.getenv("ANALYTICS_TENANT_ID", "tenant_a")
# Prompt/模型版本与请求级成本预算。
ANALYTICS_PROMPT_DIR = Path(
    os.getenv(
        "ANALYTICS_PROMPT_DIR",
        str(PROJECT_ROOT / "configs" / "analytics" / "prompts"),
    )
)
ANALYTICS_REQUEST_BUDGET = float(
    os.getenv("ANALYTICS_REQUEST_BUDGET", "0.05")
)
ANALYTICS_MODEL_CALL_COST = float(
    os.getenv("ANALYTICS_MODEL_CALL_COST", "0.002")
)
