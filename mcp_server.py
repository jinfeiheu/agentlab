"""MCP server:公共知识库工具(stdio 或 streamable HTTP)。"""

import argparse

from mcp.server.fastmcp import FastMCP

from config import DOCS_DIR
from rag import format_docs, load_documents, split_documents
from retrieval import build_pgvector_hybrid_retriever

mcp = FastMCP("agentlab-mcp")
_retriever = None
_chunks = None


def _get_retriever():
    """首次调用时构建混合检索器,进程内复用。"""
    global _retriever
    if _retriever is None:
        _retriever = build_pgvector_hybrid_retriever()
    return _retriever


def _get_chunks():
    """读取并切分公共语料,进程内复用。"""
    global _chunks
    if _chunks is None:
        _chunks = split_documents(load_documents(DOCS_DIR))
    return _chunks


@mcp.tool()
def search_docs(query: str) -> str:
    """Search the public knowledge base."""
    docs = _get_retriever().invoke(query)
    if not docs:
        return "知识库中没有找到相关内容。"
    return format_docs(docs[:3])


@mcp.tool()
def list_sources() -> list[str]:
    """List public knowledge base sources as file#section."""
    return sorted(
        {
            f"{doc.metadata.get('source', '')}#{doc.metadata.get('section', '')}"
            for doc in _get_chunks()
        }
    )


@mcp.tool()
def doc_stats() -> dict:
    """Return document and chunk counts by source."""
    chunks = _get_chunks()
    by_source: dict[str, int] = {}
    for doc in chunks:
        source = str(doc.metadata.get("source", "unknown"))
        by_source[source] = by_source.get(source, 0) + 1
    return {
        "documents": len(by_source),
        "chunks": len(chunks),
        "by_source": by_source,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AgentLab MCP knowledge server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8811)
    args = parser.parse_args()
    if args.transport == "streamable-http":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
