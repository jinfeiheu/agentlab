from langchain_core.documents import Document

from agentlab.config import DOCS_DIR
from agentlab.rag_agent.rag.loaders import (
    build_inmemory_retriever,
    format_docs,
    load_documents,
    split_documents,
)
from tests.fakes import FakeEmbeddings


def test_load_documents_reads_markdown_dir(tmp_path):
    (tmp_path / "a.md").write_text("# A\n\n内容", encoding="utf-8")
    docs = load_documents(tmp_path)
    assert len(docs) == 1
    assert docs[0].metadata["source"] == "a.md"


def test_split_documents_produces_multiple_chunks():
    docs = [
        Document(
            page_content="## 一\n\n" + "第一段。" * 200,
            metadata={"source": "k.md"},
        )
    ]
    chunks = split_documents(docs, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    assert all(chunk.page_content for chunk in chunks)
    assert all(chunk.metadata["source"] == "k.md" for chunk in chunks)
    assert all(chunk.metadata["section"] == "一" for chunk in chunks)


def test_split_documents_assigns_stable_chunk_ids():
    chunks = split_documents(load_documents(DOCS_DIR))
    ids = [chunk.metadata["chunk_id"] for chunk in chunks]
    assert len(ids) == len(set(ids))
    assert all(
        chunk.metadata["source"] and chunk.metadata["section"] for chunk in chunks
    )
    assert ids == [
        chunk.metadata["chunk_id"]
        for chunk in split_documents(load_documents(DOCS_DIR))
    ]


def test_build_inmemory_retriever_uses_injected_embeddings(tmp_path):
    (tmp_path / "a.md").write_text(
        "## Checkpointer\n\ncheckpointer 保存状态。\n\n## 其它\n\n无关内容。",
        encoding="utf-8",
    )
    retriever = build_inmemory_retriever(tmp_path, embeddings=FakeEmbeddings())
    docs = retriever.invoke("checkpointer")
    assert len(docs) == 2
    assert {doc.metadata["section"] for doc in docs} == {"Checkpointer", "其它"}


def test_format_docs_includes_source_section_and_content():
    out = format_docs(
        [
            Document(
                page_content="checkpointer 保存状态",
                metadata={"source": "k.md", "section": "Checkpointer"},
            )
        ]
    )
    assert "k.md#Checkpointer" in out
    assert "checkpointer 保存状态" in out
