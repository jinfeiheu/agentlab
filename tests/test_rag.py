from langchain_core.documents import Document

from rag import format_docs, split_documents


def test_split_documents_produces_multiple_chunks():
    docs = [Document(page_content="第一段。" * 200, metadata={"source": "k.md"})]
    chunks = split_documents(docs, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    assert all(chunk.page_content for chunk in chunks)
    assert all(chunk.metadata["source"] == "k.md" for chunk in chunks)


def test_format_docs_includes_source_and_content():
    out = format_docs(
        [Document(page_content="checkpointer 保存状态", metadata={"source": "k.md"})]
    )
    assert "k.md" in out
    assert "checkpointer 保存状态" in out
