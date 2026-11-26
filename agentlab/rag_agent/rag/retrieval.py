"""混合检索:向量召回 + BM25 关键词召回 + RRF 融合。"""

import logging
import re

import jieba
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import BaseModel
from rank_bm25 import BM25Okapi

jieba.setLogLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# Python 3 的 str 正则里 \w 已包含中文,无需额外写 CJK 范围。
_TOKEN_RE = re.compile(r"\w+")
_SOURCE_RE = re.compile(r"\[来源:([^\]]+)\]")
_CANDIDATES = 8
EMBEDDING_DIM = 1024

_RERANK_PROMPT = """你是一个检索结果重排器。请根据用户问题,给每个候选片段打 0-10 分。
评分标准:
- 10 分:直接包含回答问题的关键事实
- 5 分:部分相关
- 0 分:与问题无关
只输出 JSON,格式为 {{"scores":[{{"chunk_id":"候选 id","score":0}}]}}。不要输出其它文字。

用户问题:{query}

候选片段:
{candidates}
"""


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


def build_pgvector_hybrid_retriever(
    *,
    docs_dir=None,
    collection_name: str | None = None,
) -> HybridRetriever:
    """从 pgvector collection 构建混合检索器;默认仍使用 docs / PG_COLLECTION。"""
    from agentlab.config import DATABASE_URL, DOCS_DIR, PG_COLLECTION
    from langchain_postgres import PGVector
    from agentlab.models import build_embeddings
    from agentlab.rag_agent.rag.loaders import load_documents, split_documents

    docs_dir = docs_dir or DOCS_DIR
    collection_name = collection_name or PG_COLLECTION
    store = PGVector(
        embeddings=build_embeddings(),
        connection=DATABASE_URL,
        collection_name=collection_name,
        embedding_length=EMBEDDING_DIM,
    )
    chunks = split_documents(load_documents(docs_dir))
    return build_hybrid_retriever(
        store.as_retriever(search_kwargs={"k": _CANDIDATES}),
        chunks,
    )


class RerankItem(BaseModel):
    """单个候选片段的重排分数。"""

    chunk_id: str
    score: int


class RerankScores(BaseModel):
    """LLM 重排的结构化输出。"""

    scores: list[RerankItem]


class LLMReranker:
    """用 LLM 给候选片段打分并重排,异常时回退原顺序。"""

    def __init__(self, model, top_n: int = 3):
        self.model = model
        self.top_n = top_n

    def rerank(self, query: str, docs: list[Document]) -> list[Document]:
        if not docs:
            return []
        ids = [str(doc.metadata.get("chunk_id", "")) for doc in docs]
        if any(not chunk_id for chunk_id in ids):
            return docs[: self.top_n]
        candidates = "\n\n".join(
            f"chunk_id: {chunk_id}\n{doc.page_content[:400]}"
            for chunk_id, doc in zip(ids, docs)
        )
        try:
            structured = self.model.with_structured_output(
                RerankScores, method="json_mode"
            )
            result = structured.invoke(
                _RERANK_PROMPT.format(query=query, candidates=candidates)
            )
            score_by_id = {
                item.chunk_id: item.score for item in result.scores
            }
        except Exception:  # noqa: BLE001 - rerank 失败时退回原顺序
            return docs[: self.top_n]
        if not set(ids).issubset(score_by_id):
            return docs[: self.top_n]
        ranked = sorted(
            docs,
            key=lambda doc: score_by_id[str(doc.metadata["chunk_id"])],
            reverse=True,
        )
        return ranked[: self.top_n]


class CrossEncoderReranker:
    """专用 cross-encoder reranker 适配器,默认 bge-reranker-v2-m3。"""

    def __init__(
        self,
        model_name: str,
        top_n: int = 8,
        *,
        device: str = "cpu",
        batch_size: int = 8,
    ):
        self.model_name = model_name
        self.top_n = top_n
        self.device = device
        self.batch_size = batch_size
        self._model = None

    def _load(self):
        """延迟加载模型,避免 import 时下载或占用内存。"""
        from sentence_transformers import CrossEncoder

        return CrossEncoder(
            self.model_name, device=self.device, max_length=512
        )

    @staticmethod
    def _document_text(doc: Document) -> str:
        """把来源和章节标题拼进候选,章节名对短片段很关键。"""
        source = doc.metadata.get("source", "")
        section = doc.metadata.get("section", "")
        label = f"{source}#{section}" if section else source
        return f"{label}\n{doc.page_content}" if label else doc.page_content

    def rerank(self, query: str, docs: list[Document]) -> list[Document]:
        if not docs:
            return []
        if self._model is None:
            self._model = self._load()
        pairs = [(query, self._document_text(doc)) for doc in docs]
        scores = self._model.predict(
            pairs, batch_size=self.batch_size
        )
        ranked = sorted(
            zip(docs, scores),
            key=lambda item: float(item[1]),
            reverse=True,
        )
        return [doc for doc, _score in ranked[: self.top_n]]


class ChainReranker:
    """按顺序串联多个 reranker,前一层输出作为后一层输入。"""

    def __init__(self, rerankers: list):
        self.rerankers = rerankers

    def rerank(self, query: str, docs: list[Document]) -> list[Document]:
        for reranker in self.rerankers:
            docs = reranker.rerank(query, docs)
        return docs


def build_reranker(
    *,
    use_model: bool,
    use_llm: bool,
    model_name: str,
    device: str = "cpu",
    model_top_n: int = 8,
    llm_top_n: int = 3,
):
    """按配置组装 reranker;专用模型是默认路径,LLM rerank 可选叠加。"""
    rerankers: list = []
    if use_model:
        rerankers.append(
            CrossEncoderReranker(
                model_name, top_n=model_top_n, device=device
            )
        )
    if use_llm:
        from agentlab.models import build_judge_model

        rerankers.append(
            LLMReranker(build_judge_model(), top_n=llm_top_n)
        )
    if not rerankers:
        return None
    if len(rerankers) == 1:
        return rerankers[0]
    return ChainReranker(rerankers)


def extract_sources(text: str) -> list[str]:
    """提取回答中的 [来源:文件#章节] 标记。"""
    return [item.strip() for item in _SOURCE_RE.findall(text) if item.strip()]
