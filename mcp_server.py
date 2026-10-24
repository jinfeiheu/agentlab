"""MCP stdio server:只暴露公共知识库检索工具。"""

from mcp.server.fastmcp import FastMCP

from rag import format_docs
from retrieval import build_pgvector_hybrid_retriever

mcp = FastMCP("agentlab-mcp")
_retriever = None


def _get_retriever():
    """首次调用时构建混合检索器,进程内复用。"""
    global _retriever
    if _retriever is None:
        _retriever = build_pgvector_hybrid_retriever()
    return _retriever


@mcp.tool()
def search_docs(query: str) -> str:
    """Search the public knowledge base."""
    docs = _get_retriever().invoke(query)
    if not docs:
        return "知识库中没有找到相关内容。"
    return format_docs(docs[:3])


if __name__ == "__main__":
    mcp.run(transport="stdio")
