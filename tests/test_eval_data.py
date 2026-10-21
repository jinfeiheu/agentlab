from config import DOCS_DIR, GOLDEN_PATH
from eval.data import load_golden
from rag import load_documents, split_documents


def test_golden_has_27_cases_and_4_unanswerable():
    items = load_golden(GOLDEN_PATH)
    assert len(items) == 27
    assert sum(not item.answerable for item in items) == 4
    assert len({item.id for item in items}) == 27


def test_golden_sources_exist():
    for item in load_golden(GOLDEN_PATH):
        for source in item.expected_sources:
            assert (DOCS_DIR / source.split("#")[0]).exists()


def test_golden_source_sections_exist():
    sections = {
        (chunk.metadata["source"], chunk.metadata["section"])
        for chunk in split_documents(load_documents(DOCS_DIR))
    }
    for item in load_golden(GOLDEN_PATH):
        for source in item.expected_sources:
            file_name, _, section = source.partition("#")
            assert (file_name, section) in sections


def test_golden_chunk_ids_exist():
    chunk_ids = {
        chunk.metadata["chunk_id"]
        for chunk in split_documents(load_documents(DOCS_DIR))
    }
    for item in load_golden(GOLDEN_PATH):
        for chunk_id in item.relevant_chunk_ids:
            assert chunk_id in chunk_ids


def test_golden_has_multichunk_cases():
    items = load_golden(GOLDEN_PATH)
    assert sum(len(item.relevant_chunk_ids) > 1 for item in items) >= 6


def test_answerable_items_have_sources_and_chunks():
    for item in load_golden(GOLDEN_PATH):
        if item.answerable:
            assert item.expected_sources
            assert item.relevant_chunk_ids
        else:
            assert item.relevant_chunk_ids == []
