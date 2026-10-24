"""pgvector 文档摄入的单元与集成测试。"""

import os

import pytest
from langchain_core.documents import Document

import ingest
from config import DATABASE_URL, DOCS_DIR, PG_COLLECTION
from ingest import build_vector_store, main
from rag import load_documents, split_documents

integration = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="需要真实 Postgres 与 Ollama;设置 RUN_INTEGRATION=1 后运行",
)


def test_chunks_have_required_metadata():
    chunks = split_documents(load_documents(DOCS_DIR))
    assert all({"source", "section", "chunk_id"} <= set(c.metadata) for c in chunks)
    assert len({c.metadata["chunk_id"] for c in chunks}) == len(chunks)


def test_build_vector_store_uses_config(monkeypatch):
    captured = {}
    sentinel = object()

    def fake_from_documents(documents, embedding, **kwargs):
        captured["documents"] = documents
        captured["embedding"] = embedding
        captured["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(ingest.PGVector, "from_documents", fake_from_documents)
    monkeypatch.setattr(ingest, "build_embeddings", lambda: "fake-embedding")
    docs = [Document(page_content="内容", metadata={"chunk_id": "a.md::0"})]
    store = ingest.build_vector_store(docs, reset=True)
    assert store is sentinel
    assert captured["documents"] == docs
    assert captured["embedding"] == "fake-embedding"
    kwargs = captured["kwargs"]
    assert kwargs["connection"] == DATABASE_URL
    assert kwargs["collection_name"] == PG_COLLECTION
    assert kwargs["embedding_length"] == 1024
    assert kwargs["pre_delete_collection"] is True
    assert kwargs["use_jsonb"] is True


def test_main_ingests_chunks(monkeypatch, capsys):
    docs = [Document(page_content="a")]
    chunks = [Document(page_content="a", metadata={"chunk_id": "a::0"})]
    calls = []
    monkeypatch.setattr(ingest, "load_documents", lambda _: docs)
    monkeypatch.setattr(ingest, "split_documents", lambda _: chunks)
    monkeypatch.setattr(
        ingest,
        "build_vector_store",
        lambda items, reset=False, **kwargs: calls.append(
            (items, reset, kwargs)
        ),
    )
    ingest.main(reset=True)
    assert calls[0][0] == chunks
    assert calls[0][1] is True
    assert calls[0][2]["collection_name"] == PG_COLLECTION
    assert "1" in capsys.readouterr().out


def test_build_vector_store_can_load_docs_dir(monkeypatch, tmp_path):
    captured = {}
    docs = [Document(page_content="a")]
    chunks = [Document(page_content="a", metadata={"chunk_id": "a::0"})]

    def fake_from_documents(documents, embedding, **kwargs):
        captured["docs"] = documents
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(ingest.PGVector, "from_documents", fake_from_documents)
    monkeypatch.setattr(ingest, "build_embeddings", lambda: "fake-embedding")
    monkeypatch.setattr(ingest, "load_documents", lambda path: docs)
    monkeypatch.setattr(ingest, "split_documents", lambda items: chunks)
    ingest.build_vector_store(
        docs_dir=tmp_path, collection_name="docs_hard"
    )
    assert captured["docs"] == chunks
    assert captured["kwargs"]["collection_name"] == "docs_hard"


def test_build_vector_store_accepts_collection_override(monkeypatch):
    captured = {}

    def fake_from_documents(documents, embedding, **kwargs):
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(ingest.PGVector, "from_documents", fake_from_documents)
    monkeypatch.setattr(ingest, "build_embeddings", lambda: "fake-embedding")
    ingest.build_vector_store(
        [Document(page_content="a")], collection_name="docs_hard"
    )
    assert captured["kwargs"]["collection_name"] == "docs_hard"


def test_main_accepts_docs_dir_and_collection(monkeypatch, tmp_path, capsys):
    seen = {}
    monkeypatch.setattr(
        ingest,
        "load_documents",
        lambda path: seen.setdefault("docs_dir", path) and [Document(page_content="a")],
    )
    monkeypatch.setattr(
        ingest, "split_documents", lambda docs: [Document(page_content="a")]
    )
    monkeypatch.setattr(
        ingest,
        "build_vector_store",
        lambda items, reset=False, **kwargs: seen.setdefault(
            "collection", kwargs.get("collection_name")
        ),
    )
    ingest.main(
        docs_dir=tmp_path, collection_name="docs_hard", reset=True
    )
    assert seen["docs_dir"] == tmp_path
    assert seen["collection"] == "docs_hard"
    out = capsys.readouterr().out
    assert "docs_hard" in out


@pytest.mark.integration
@integration
def test_build_vector_store_roundtrip():
    store = build_vector_store(
        split_documents(load_documents(DOCS_DIR)), reset=True
    )
    hits = store.similarity_search("checkpointer 保存状态", k=2)
    assert hits
    assert all("chunk_id" in hit.metadata for hit in hits)
