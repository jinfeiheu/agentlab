"""把 data/docs 切块并写入 pgvector。"""

import argparse
from pathlib import Path

from langchain_core.documents import Document
from langchain_postgres import PGVector

from config import DATABASE_URL, DOCS_DIR, PG_COLLECTION
from models import build_embeddings
from rag import load_documents, split_documents

EMBEDDING_DIM = 1024


def build_vector_store(
    docs: list[Document] | None = None,
    *,
    reset: bool = False,
    collection_name: str = PG_COLLECTION,
    docs_dir=DOCS_DIR,
) -> PGVector:
    """把文档写入 pgvector;不传 docs 时从 docs_dir 加载并切分。"""
    if docs is None:
        docs = split_documents(load_documents(docs_dir))
    return PGVector.from_documents(
        docs,
        build_embeddings(),
        connection=DATABASE_URL,
        collection_name=collection_name,
        embedding_length=EMBEDDING_DIM,
        pre_delete_collection=reset,
        use_jsonb=True,
    )


def main(
    reset: bool = False,
    *,
    docs_dir=DOCS_DIR,
    collection_name: str = PG_COLLECTION,
) -> None:
    """读取指定目录,切块并写入 pgvector;默认行为仍是 data/docs -> docs。"""
    chunks = split_documents(load_documents(docs_dir))
    build_vector_store(
        chunks, reset=reset, collection_name=collection_name
    )
    print(
        f"已摄入 {len(chunks)} 个 chunks 到 {collection_name}"
        f"(reset={reset}, docs_dir={docs_dir})"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="把 Markdown 语料摄入 pgvector")
    parser.add_argument("--reset", action="store_true", help="重建 collection")
    parser.add_argument(
        "--docs-dir", default=str(DOCS_DIR), help="语料目录"
    )
    parser.add_argument(
        "--collection", default=PG_COLLECTION, help="pgvector collection 名"
    )
    args = parser.parse_args()
    main(
        reset=args.reset,
        docs_dir=Path(args.docs_dir),
        collection_name=args.collection,
    )
