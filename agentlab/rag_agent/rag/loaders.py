"""RAG 链路:目录加载 -> 按标题切分 -> 稳定 chunk_id -> 内存向量检索。"""

from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from agentlab.config import RAG_TOP_K
from agentlab.models import build_embeddings

_HEADERS = [("#", "title"), ("##", "section")]


def load_documents(docs_dir: Path) -> list[Document]:
    """按文件名顺序读取目录下的 Markdown 文档。"""
    return [
        Document(
            page_content=path.read_text(encoding="utf-8"),
            metadata={"source": path.name},
        )
        for path in sorted(docs_dir.glob("*.md"))
    ]


def split_documents(
    docs: list[Document],
    chunk_size: int = 400,
    chunk_overlap: int = 100,
) -> list[Document]:
    """先按 Markdown 标题切小节,超长小节再按中文分隔符递归切分。"""
    header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=_HEADERS)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
        keep_separator="end",
    )

    chunks: list[Document] = []
    for doc in docs:
        source = doc.metadata.get("source", "未知来源")
        index = 0
        for section_doc in header_splitter.split_text(doc.page_content):
            section = (
                section_doc.metadata.get("section")
                or section_doc.metadata.get("title")
                or "正文"
            )
            pieces = text_splitter.split_text(section_doc.page_content)
            for piece in pieces:
                if not piece.strip():
                    continue
                chunks.append(
                    Document(
                        page_content=piece.strip(),
                        metadata={
                            "source": source,
                            "section": section,
                            "chunk_id": f"{source}::{index}",
                        },
                    )
                )
                index += 1
    return chunks


def format_docs(docs: list[Document]) -> str:
    """把检索结果拼成带“文件#章节”来源的上下文。"""
    parts = []
    for doc in docs:
        source = doc.metadata.get("source", "未知来源")
        section = doc.metadata.get("section")
        label = f"{source}#{section}" if section else source
        parts.append(f"[来源:{label}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def build_inmemory_retriever(
    docs_dir: Path,
    embeddings: Embeddings | None = None,
) -> BaseRetriever:
    """加载语料、切分、嵌入并返回内存检索器。"""
    if embeddings is None:
        embeddings = build_embeddings()
    chunks = split_documents(load_documents(docs_dir))
    store = InMemoryVectorStore.from_documents(chunks, embeddings)
    return store.as_retriever(search_kwargs={"k": RAG_TOP_K})
