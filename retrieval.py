"""混合检索:向量召回 + BM25 关键词召回 + RRF 融合。"""

import logging
import re

import jieba
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from rank_bm25 import BM25Okapi

jieba.setLogLevel(logging.ERROR)

# Python 3 的 str 正则里 \w 已包含中文,无需额外写 CJK 范围。
_TOKEN_RE = re.compile(r"\w+")
_CANDIDATES = 8


def tokenize(text: str) -> list[str]:
    """用 jieba 切词,过滤空白和纯标点。"""
    return [
        token.lower()
        for token in jieba.lcut(text)
        if _TOKEN_RE.fullmatch(token)
    ]


def _doc_key(doc: Document) -> str:
    """RRF 去重键:优先 chunk_id,其次正文。"""
    return str(doc.metadata.get("chunk_id") or doc.page_content)


def rrf_fuse(
    vector_docs: list[Document],
    bm25_docs: list[Document],
    *,
    k: int = 60,
    top_n: int = 6,
) -> list[Document]:
    """Reciprocal Rank Fusion:两路排名的倒数之和。"""
    scores: dict[str, float] = {}
    docs_by_key: dict[str, Document] = {}
    for docs in (vector_docs, bm25_docs):
        for rank, doc in enumerate(docs, start=1):
            key = _doc_key(doc)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            docs_by_key.setdefault(key, doc)
    ordered = sorted(scores, key=scores.get, reverse=True)
    return [docs_by_key[key] for key in ordered[:top_n]]


class HybridRetriever:
    """向量与 BM25 各取候选,再用 RRF 融合。"""

    def __init__(
        self,
        vector_retriever: BaseRetriever,
        bm25_docs: list[Document],
        *,
        top_n: int = 6,
    ):
        self.vector_retriever = vector_retriever
        self.bm25_docs = bm25_docs
        self.top_n = top_n
        corpus = [tokenize(doc.page_content) for doc in bm25_docs]
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def _bm25_search(self, query: str) -> list[Document]:
        """BM25 取前 8 个正分文档。"""
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(
            range(len(scores)), key=lambda index: scores[index], reverse=True
        )
        return [
            self.bm25_docs[index]
            for index in ranked[:_CANDIDATES]
            if scores[index] > 0
        ]

    def invoke(self, query: str) -> list[Document]:
        """同步检索,供工具与测试调用。"""
        vector_docs = list(self.vector_retriever.invoke(query))[:_CANDIDATES]
        return rrf_fuse(
            vector_docs,
            self._bm25_search(query),
            top_n=self.top_n,
        )

    async def ainvoke(self, query: str) -> list[Document]:
        """异步入口;底层检索是同步的。"""
        return self.invoke(query)


def build_hybrid_retriever(
    vector_retriever: BaseRetriever,
    all_docs: list[Document],
    *,
    top_n: int = 6,
) -> HybridRetriever:
    """用全部 chunk 构建 BM25,并与向量检索器组合。"""
    return HybridRetriever(vector_retriever, all_docs, top_n=top_n)
