"""模型工厂:对话、嵌入、裁判统一从这里创建。"""

from langchain_deepseek import ChatDeepSeek
from langchain_ollama import OllamaEmbeddings

from config import DEEPSEEK_MODEL, EMBED_MODEL, OLLAMA_BASE_URL


def build_chat_model(*, temperature: float = 0) -> ChatDeepSeek:
    """创建对话模型。"""
    return ChatDeepSeek(model=DEEPSEEK_MODEL, temperature=temperature)


def build_embeddings() -> OllamaEmbeddings:
    """创建本地 bge-m3 嵌入模型。"""
    return OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)


def build_judge_model() -> ChatDeepSeek:
    """创建评测裁判模型,温度固定为 0 保证可复现。"""
    return build_chat_model(temperature=0)
