"""模型工厂:对话、嵌入、裁判统一从这里创建。"""

from langchain_core.runnables import Runnable
from langchain_deepseek import ChatDeepSeek
from langchain_ollama import ChatOllama, OllamaEmbeddings

from agentlab.config import DEEPSEEK_MODEL, EMBED_MODEL, OLLAMA_BASE_URL


def build_chat_model(
    *, temperature: float = 0, model: str | None = None
) -> ChatDeepSeek:
    """创建对话模型；model 为空时使用 DEEPSEEK_MODEL。"""
    return ChatDeepSeek(
        model=model or DEEPSEEK_MODEL, temperature=temperature
    )


def build_embeddings() -> OllamaEmbeddings:
    """创建本地 bge-m3 嵌入模型。"""
    return OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)


def build_judge_model() -> ChatDeepSeek:
    """创建评测裁判模型,温度固定为 0 保证可复现。"""
    return build_chat_model(temperature=0)


def build_fallback_model() -> ChatOllama:
    """本地 Ollama fallback;仅用于非工具调用。"""
    return ChatOllama(model="qwen3:8b", temperature=0, reasoning=False)


def build_invoke_with_fallback() -> Runnable:
    """主模型失败时切换 Ollama;不要用于需要 bind_tools 的 agent。"""
    return build_chat_model().with_fallbacks([build_fallback_model()])
