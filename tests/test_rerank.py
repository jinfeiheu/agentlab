"""LLM rerank 与引用提取测试。"""

from langchain_core.documents import Document

from retrieval import (
    ChainReranker,
    CrossEncoderReranker,
    LLMReranker,
    RerankItem,
    RerankScores,
    build_reranker,
    extract_sources,
)
from tests.fakes import FailingRunnable, FakeRunnable


def _doc(chunk_id: str) -> Document:
    return Document(page_content=f"内容 {chunk_id}", metadata={"chunk_id": chunk_id})


def _scores(**scores: int) -> RerankScores:
    return RerankScores(
        scores=[
            RerankItem(chunk_id=chunk_id, score=score)
            for chunk_id, score in scores.items()
        ]
    )


def test_llm_reranker_orders_by_scores():
    fake = FakeRunnable(_scores(a=1, b=9))
    docs = [_doc("a"), _doc("b")]
    out = LLMReranker(fake, top_n=2).rerank("q", docs)
    assert [doc.metadata["chunk_id"] for doc in out] == ["b", "a"]


def test_reranker_limits_top_n():
    fake = FakeRunnable(_scores(a=1, b=9, c=5))
    docs = [_doc("a"), _doc("b"), _doc("c")]
    out = LLMReranker(fake, top_n=2).rerank("q", docs)
    assert [doc.metadata["chunk_id"] for doc in out] == ["b", "c"]


def test_reranker_falls_back_on_bad_output():
    docs = [_doc("a")]
    assert LLMReranker(FailingRunnable()).rerank("q", docs) == docs


def test_reranker_falls_back_when_candidate_missing():
    fake = FakeRunnable(_scores(a=9))
    docs = [_doc("a"), _doc("b")]
    assert LLMReranker(fake, top_n=2).rerank("q", docs) == docs


def test_reranker_handles_empty_docs():
    assert LLMReranker(FakeRunnable(_scores())).rerank("q", []) == []


def test_extract_sources():
    assert extract_sources("答案 [来源:a.md#x]") == ["a.md#x"]


def test_extract_sources_multiple():
    text = "[来源:a.md#x] 和 [来源:b.md#y]"
    assert extract_sources(text) == ["a.md#x", "b.md#y"]


class FakeCrossEncoder:
    """记录输入并按预设分数返回,避免加载真实模型。"""

    def __init__(self, scores):
        self.scores = scores
        self.calls = []

    def predict(self, pairs, batch_size=8):
        self.calls.append((pairs, batch_size))
        return self.scores


def test_cross_encoder_reranker_orders_by_scores(monkeypatch):
    reranker = CrossEncoderReranker("fake-model", top_n=2)
    fake = FakeCrossEncoder([1.0, 9.0])
    monkeypatch.setattr(reranker, "_load", lambda: fake)
    docs = [_doc("a"), _doc("b")]
    out = reranker.rerank("q", docs)
    assert [doc.metadata["chunk_id"] for doc in out] == ["b", "a"]
    assert fake.calls[0][0] == [("q", "内容 a"), ("q", "内容 b")]


def test_cross_encoder_includes_source_and_section(monkeypatch):
    reranker = CrossEncoderReranker("fake-model")
    fake = FakeCrossEncoder([9.0])
    monkeypatch.setattr(reranker, "_load", lambda: fake)
    docs = [
        Document(
            page_content="正文",
            metadata={"source": "a.md", "section": "Reducer"},
        )
    ]
    reranker.rerank("q", docs)
    assert fake.calls[0][0] == [("q", "a.md#Reducer\n正文")]


def test_cross_encoder_handles_empty_docs():
    reranker = CrossEncoderReranker("fake-model")
    assert reranker.rerank("q", []) == []


class ReverseReranker:
    def rerank(self, query, docs):
        return list(reversed(docs))


class KeepReranker:
    def rerank(self, query, docs):
        return docs


def test_chain_reranker_applies_in_order():
    docs = [_doc("a"), _doc("b"), _doc("c")]
    chain = ChainReranker([KeepReranker(), ReverseReranker()])
    out = chain.rerank("q", docs)
    assert [doc.metadata["chunk_id"] for doc in out] == ["c", "b", "a"]


def test_build_reranker_defaults_to_model():
    reranker = build_reranker(
        use_model=True,
        use_llm=False,
        model_name="fake-model",
    )
    assert isinstance(reranker, CrossEncoderReranker)


def test_build_reranker_can_be_disabled():
    assert build_reranker(
        use_model=False,
        use_llm=False,
        model_name="fake-model",
    ) is None
