"""集中读取环境变量,避免各模块散落 os.getenv。"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = DATA_DIR / "docs"
GOLDEN_PATH = BASE_DIR / "eval" / "golden.jsonl"


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agentlab"
)
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")
AUTH_SECRET = os.getenv("AUTH_SECRET", "dev-only-change-me")
TRACING_ENABLED = _env_bool("TRACING_ENABLED", False)
PHOENIX_ENDPOINT = os.getenv(
    "PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces"
)
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
RAG_MODE = os.getenv("RAG_MODE", "baseline")
RERANK_ENABLED = _env_bool("RERANK_ENABLED", False)
USE_DB = _env_bool("USE_DB", False)
USE_MCP = _env_bool("USE_MCP", False)
PG_COLLECTION = os.getenv("PG_COLLECTION", "agentlab_docs")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "60"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
CONTEXT_MAX_TOKENS = int(os.getenv("CONTEXT_MAX_TOKENS", "6000"))
ENABLE_AUTO_MEMORY = _env_bool("ENABLE_AUTO_MEMORY", False)
