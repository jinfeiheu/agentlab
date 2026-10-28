"""共享测试替身:离线测试不依赖 DeepSeek、Ollama 或 Postgres。"""

from dataclasses import dataclass
from types import SimpleNamespace

from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage, AIMessageChunk


class FakeRunnable:
    """固定返回同一个结果,用于测试 judge / 模型调用。"""

    def __init__(self, result):
        self.result = result

    def invoke(self, *args, **kwargs):
        return self.result

    async def ainvoke(self, *args, **kwargs):
        return self.result

    def with_structured_output(self, *args, **kwargs):
        return self


class FailingRunnable:
    """模拟模型/接口异常。"""

    def invoke(self, *args, **kwargs):
        raise RuntimeError("fake failure")

    async def ainvoke(self, *args, **kwargs):
        raise RuntimeError("fake failure")


class FakeRetriever:
    """返回预设文档,避免真实向量检索。"""

    def __init__(self, docs):
        self.docs = docs

    def invoke(self, query):
        return self.docs

    async def ainvoke(self, query):
        return self.docs


class FakeEmbeddings(Embeddings):
    """确定性向量,供 InMemoryStore 的索引使用。"""

    def __init__(self, dim: int = 4):
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        total = sum(ord(char) for char in text)
        return [float((total + i) % 10) for i in range(self.dim)]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)

    async def aembed_query(self, text: str) -> list[float]:
        return self.embed_query(text)


class FakeRuntime:
    """模拟 LangGraph 注入的 ToolRuntime,只保留常用字段。"""

    def __init__(self, context, store=None):
        self.context = context
        self.store = store


class RecordingGraph:
    """记录调用配置与 context 并返回固定回答,用于 API 测试。"""

    def __init__(self, answer: str = "fake answer"):
        self.answer = answer
        self.configs = []
        self.contexts = []

    async def ainvoke(self, payload, config=None, **kwargs):
        self.configs.append(config)
        self.contexts.append(kwargs.get("context"))
        return {"messages": [AIMessage(content=self.answer)]}

    async def astream(self, payload, config=None, stream_mode=None, **kwargs):
        self.configs.append(config)
        self.contexts.append(kwargs.get("context"))
        yield ("messages", (AIMessageChunk(content=self.answer), {}))
        yield ("updates", {})

    def get_state(self, config):
        return SimpleNamespace(interrupts=())


@dataclass
class FakeServices:
    """api.Services 的测试替身。"""

    graph: object
    retriever: object = None
    db_check: object = None
    model: object = None
    memory_store: object = None


def fake_services(graph=None, retriever=None) -> FakeServices:
    """创建默认使用 RecordingGraph 的测试服务集合。"""
    return FakeServices(graph=graph or RecordingGraph(), retriever=retriever)


class FakeToolCallRequest:
    """模拟工具调用请求,供安全包装器测试。"""

    def __init__(self, name: str, args: dict, call_id: str = "call-1"):
        self.tool_call = {"name": name, "args": args, "id": call_id}


def bearer(token: str) -> dict[str, str]:
    """构造 Authorization 请求头。"""
    return {"Authorization": f"Bearer {token}"}


def auth_client(services):
    """创建已登录的 TestClient;延迟导入 serve 依赖,Phase 1 也能导入本模块。"""
    from fastapi.testclient import TestClient

    from agentlab.api.app import create_app
    from agentlab.security.auth import sign_token

    return TestClient(create_app(services=services)), sign_token("user_alice")
