"""RAG 链路:加载 -> 切分 -> bge-m3 嵌入 -> 内存向量库 -> 检索器。"""

import os
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_document(path: Path) -> Document:
    """读取本地 Markdown 文件,包装成带来源信息的 Document。"""
    return Document(
        page_content=path.read_text(encoding="utf-8"),
        metadata={"source": path.name},
    )


def split_documents(
    docs: list[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 80,
) -> list[Document]:
    """按中文友好的分隔符切分文档。"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    )
    return splitter.split_documents(docs)


def format_docs(docs: list[Document]) -> str:
    """把检索结果拼成带来源的上下文。"""
    parts = []
    for doc in docs:
        source = doc.metadata.get("source", "未知来源")
        parts.append(f"[来源:{source}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def build_retriever(knowledge_path: Path) -> BaseRetriever:
    """加载知识库、切分、嵌入并返回内存检索器。"""
    embeddings = OllamaEmbeddings(
        model=os.getenv("OLLAMA_EMBED_MODEL", "bge-m3"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    )
    chunks = split_documents([load_document(knowledge_path)])
    store = InMemoryVectorStore.from_documents(chunks, embeddings)
    top_k = int(os.getenv("RAG_TOP_K", "3"))
    return store.as_retriever(search_kwargs={"k": top_k})
