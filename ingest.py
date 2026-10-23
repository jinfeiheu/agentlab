"""把 data/docs 切块并写入 pgvector。"""

import argparse

from langchain_core.documents import Document
from langchain_postgres import PGVector

from config import DATABASE_URL, DOCS_DIR, PG_COLLECTION
from models import build_embeddings
from rag import load_documents, split_documents

EMBEDDING_DIM = 1024


def build_vector_store(docs: list[Document], *, reset: bool = False) -> PGVector:
    """把文档写入 pgvector;reset=True 时先删除同名 collection。"""
    return PGVector.from_documents(
        docs,
        build_embeddings(),
        connection=DATABASE_URL,
        collection_name=PG_COLLECTION,
        embedding_length=EMBEDDING_DIM,
        pre_delete_collection=reset,
        use_jsonb=True,
    )


def main(reset: bool = False) -> None:
    """读取 data/docs,切块并写入 pgvector。"""
    chunks = split_documents(load_documents(DOCS_DIR))
    build_vector_store(chunks, reset=reset)
    print(f"已摄入 {len(chunks)} 个 chunks 到 {PG_COLLECTION}(reset={reset})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="把 data/docs 摄入 pgvector")
    parser.add_argument("--reset", action="store_true", help="重建 collection")
    args = parser.parse_args()
    main(reset=args.reset)
