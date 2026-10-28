"""混合检索:分词、RRF 融合与 HybridRetriever。"""

from langchain_core.documents import Document

from agentlab.rag.retrieval import (
    HybridRetriever,
    build_hybrid_retriever,
    rrf_fuse,
    tokenize,
)


class FakeRetriever:
    def __init__(self, docs):
        self.docs = docs

    def invoke(self, query):
        return self.docs


def _doc(chunk_id: str, text: str | None = None) -> Document:
    return Document(page_content=text or chunk_id, metadata={"chunk_id": chunk_id})


def test_tokenize_chinese():
    tokens = tokenize("checkpointer 保存状态")
    assert "checkpointer" in tokens
    assert "保存" in tokens or "状态" in tokens


def test_tokenize_filters_punctuation():
    assert tokenize("，。！") == []


def test_rrf_fuse_prefers_docs_in_both_lists():
    a = _doc("a")
    b = _doc("b")
    result = rrf_fuse([a, b], [b], top_n=2)
    assert result[0].metadata["chunk_id"] == "b"


def test_rrf_fuse_dedupes_by_chunk_id():
    a = _doc("a")
    assert len(rrf_fuse([a], [a], top_n=5)) == 1


def test_hybrid_retriever_returns_top_n():
    a = _doc("a", "checkpointer 保存状态")
    b = _doc("b", "向量检索")
    hybrid = HybridRetriever(FakeRetriever([a, b]), [a, b], top_n=1)
    assert len(hybrid.invoke("checkpointer")) == 1


def test_hybrid_retriever_combines_vector_and_bm25():
    vector_only = _doc("vector", "向量召回")
    shared = _doc("shared", "状态保存")
    bm25_only = _doc("bm25", "checkpointer 关键词召回")
    extra = [_doc("extra1", "其他内容一"), _doc("extra2", "其他内容二")]
    hybrid = HybridRetriever(
        FakeRetriever([vector_only, shared]),
        [shared, bm25_only, *extra],
        top_n=3,
    )
    ids = {doc.metadata["chunk_id"] for doc in hybrid.invoke("checkpointer")}
    assert ids == {"vector", "shared", "bm25"}


def test_build_hybrid_retriever_returns_hybrid():
    hybrid = build_hybrid_retriever(FakeRetriever([]), [], top_n=2)
    assert isinstance(hybrid, HybridRetriever)
    assert hybrid.invoke("anything") == []
