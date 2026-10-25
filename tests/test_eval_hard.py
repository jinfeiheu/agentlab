"""Task 15.5：hard golden、新指标、严格 judge、分层报告与 closed-book 消融。"""

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from config import HARD_DOCS_DIR, HARD_GOLDEN_PATH
from eval.data import load_golden
from eval.judge import build_judge, judge_answer
from eval.retrieval_metrics import (
    citation_precision,
    context_precision,
    context_recall,
)
from eval.run_eval import evaluate, write_report
from eval.text_metrics import exact_match, token_f1
from rag import load_documents, split_documents
from tests.fakes import FakeRetriever, FakeRunnable


# ---------- hard golden 数据质量 ----------

_HARD_CATEGORY_COUNTS = {
    "single-hop": 30,
    "multi-hop": 25,
    "temporal-version": 10,
    "ambiguous": 10,
    "unanswerable-distractor": 15,
    "table-numeric": 10,
}


def test_hard_golden_has_100_cases_and_category_budget():
    items = load_golden(HARD_GOLDEN_PATH)
    assert len(items) == 100
    assert len({item.id for item in items}) == 100
    counts = {}
    for item in items:
        counts[item.category] = counts.get(item.category, 0) + 1
    assert counts == _HARD_CATEGORY_COUNTS


def test_hard_golden_items_are_fully_annotated():
    for item in load_golden(HARD_GOLDEN_PATH):
        assert item.difficulty in {"easy", "medium", "hard"}
        assert item.reference_answer
        assert item.key_points
        assert "search_docs" in item.expected_tools
        assert set(item.expected_tools) <= {"search_docs", "calculator"}
        if item.answerable:
            assert item.expected_sources
            assert item.relevant_chunk_ids
        else:
            assert item.relevant_chunk_ids == []


def test_hard_golden_has_visible_failure_mix():
    items = load_golden(HARD_GOLDEN_PATH)
    assert sum(item.difficulty == "hard" for item in items) >= 25
    assert sum(not item.answerable for item in items) == 15
    assert sum(len(item.relevant_chunk_ids) > 1 for item in items) >= 25


def test_hard_golden_sources_and_chunks_exist():
    chunks = split_documents(load_documents(HARD_DOCS_DIR))
    chunk_ids = {chunk.metadata["chunk_id"] for chunk in chunks}
    sections = {
        (chunk.metadata["source"], chunk.metadata["section"])
        for chunk in chunks
    }
    for item in load_golden(HARD_GOLDEN_PATH):
        for chunk_id in item.relevant_chunk_ids:
            assert chunk_id in chunk_ids, f"{item.id}: {chunk_id}"
        for source in item.expected_sources:
            file_name, _, section = source.partition("#")
            assert (file_name, section) in sections, f"{item.id}: {source}"


# ---------- 新指标 ----------


def test_context_precision_averages_precision_at_relevant_ranks():
    # 命中 rank 1 和 rank 3：(1/1 + 2/3) / 2
    assert context_precision(["a", "b", "c"], {"a", "c", "d"}, 3) == (
        pytest.approx((1 + 2 / 3) / 2)
    )
    assert context_precision(["a"], {"b"}, 1) == 0.0
    assert context_precision(["a"], set(), 1) == 0.0
    assert context_precision([], {"a"}, 3) == 0.0


def test_context_recall_is_recall_at_k():
    assert context_recall(["a", "b", "c"], {"b", "d"}, 3) == 0.5
    assert context_recall(["a"], {"a"}, 1) == 1.0
    assert context_recall([], {"a"}, 1) == 0.0


def test_citation_precision():
    assert citation_precision(["a#x", "b#y"], {"a#x", "c#z"}) == 0.5
    assert citation_precision(["a#x", "a#x"], {"a#x"}) == 1.0
    assert citation_precision([], {"a#x"}) == 0.0
    assert citation_precision(["a#x"], set()) == 0.0


def test_token_f1_and_exact_match():
    assert token_f1("chunk size 400", "chunk size 400") == 1.0
    assert token_f1("chunk size 512", "chunk size 400 overlap 100") == 0.5
    assert token_f1("", "chunk") == 0.0
    assert token_f1("", "") == 1.0
    assert exact_match("chunk  size 400", "chunk size 400") is True
    assert exact_match("chunk size 512", "chunk size 400") is False


# ---------- judge 加严与跨模型 ----------


def test_judge_prompt_includes_reference_answer():
    class RecordingJudge:
        prompt = ""

        def invoke(self, prompt):
            self.prompt = prompt
            return _judge_result()

    judge = RecordingJudge()
    judge_answer(judge, "q", "a", ["ctx"], reference_answer="参考答案事实")
    assert "参考答案事实" in judge.prompt


def test_judge_with_bad_structured_output_returns_safe_default():
    class BadJudge:
        def invoke(self, prompt):
            return {"correctness": "not-a-number"}

    result = judge_answer(BadJudge(), "q", "a", [])
    assert result.correctness == 0
    assert result.citation_support is False
    assert "judge failed" in result.reason


def test_build_judge_supports_ollama_cross_model(monkeypatch):
    captured = {}

    class FakeOllama:
        def __init__(self, **kwargs):
            captured["init"] = kwargs

        def with_structured_output(self, schema, **kwargs):
            captured["schema"] = schema
            captured["method"] = kwargs.get("method")
            return "ollama-judge"

    monkeypatch.setattr("eval.judge.ChatOllama", FakeOllama)
    assert build_judge("qwen3:8b") == "ollama-judge"
    assert captured["init"]["model"] == "qwen3:8b"
    assert captured["method"] == "json_mode"


# ---------- 分层汇总与 closed-book ----------


def _judge_result():
    from eval.judge import JudgeResult

    return JudgeResult(
        correctness=4,
        faithfulness=4,
        citation_support=True,
        reason="ok",
    )


class _Graph:
    def invoke(self, payload, config=None, **kwargs):
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "search_docs",
                            "args": {"query": "q"},
                            "id": "c1",
                        }
                    ],
                ),
                ToolMessage(
                    content="[来源:01-rag-pipeline.md#切分参数]\n内容",
                    name="search_docs",
                    tool_call_id="c1",
                ),
                AIMessage(
                    content=(
                        "chunk size 400 [来源:01-rag-pipeline.md#切分参数]"
                    )
                ),
            ]
        }


class _ExplodingRetriever:
    def invoke(self, query):
        raise AssertionError("closed-book 不应调用 retriever")


def _golden():
    from eval.data import GoldenItem

    return [
        GoldenItem(
            id="h1",
            question="chunk size 是多少?",
            answerable=True,
            difficulty="easy",
            category="single-hop",
            reference_answer="chunk size 是 400",
            expected_sources=["01-rag-pipeline.md#切分参数"],
            relevant_chunk_ids=["01-rag-pipeline.md::1"],
            key_points=["400"],
            expected_tools=["search_docs"],
        ),
        GoldenItem(
            id="h2",
            question="生产数据库密码是多少?",
            answerable=False,
            difficulty="hard",
            category="unanswerable-distractor",
            reference_answer="资料中没有生产数据库密码,应拒答",
            key_points=["拒答"],
            expected_tools=["search_docs"],
        ),
    ]


class _GraphExtraTool(_Graph):
    def invoke(self, payload, config=None, **kwargs):
        result = super().invoke(payload, config=config, **kwargs)
        result["messages"].insert(
            1,
            ToolMessage(
                content="60",
                name="calculator",
                tool_call_id="c0",
            ),
        )
        return result


class _GraphNoTools:
    def invoke(self, payload, config=None, **kwargs):
        return {"messages": [AIMessage(content="没有调用工具")]}


def test_tool_accuracy_allows_extra_safe_tool():
    report = evaluate(
        _GraphExtraTool(),
        FakeRetriever([]),
        _golden()[:1],
        FakeRunnable(_judge_result()),
    )
    assert report.rows[0]["expected_tools"] == ["search_docs"]
    assert "calculator" in report.rows[0]["actual_tools"]
    assert report.rows[0]["tool_accuracy"] is True


def test_tool_accuracy_requires_expected_tool():
    report = evaluate(
        _GraphNoTools(),
        FakeRetriever([]),
        _golden()[:1],
        FakeRunnable(_judge_result()),
    )
    assert report.rows[0]["tool_accuracy"] is False


def test_evaluate_reports_strata_by_difficulty_and_category():
    report = evaluate(
        _Graph(),
        FakeRetriever([]),
        _golden(),
        FakeRunnable(_judge_result()),
        judge_model="deepseek-flash",
    )
    assert report.strata["difficulty"]["easy"]["count"] == 1
    assert report.strata["difficulty"]["hard"]["count"] == 1
    assert report.strata["category"]["single-hop"]["count"] == 1
    row = report.rows[0]
    assert row["token_f1"] > 0
    assert row["exact_match"] is False
    assert row["citations"] == ["01-rag-pipeline.md#切分参数"]
    assert row["citation_precision"] == 1.0


def test_write_report_renders_strata(tmp_path):
    report = evaluate(
        _Graph(),
        FakeRetriever([]),
        _golden(),
        FakeRunnable(_judge_result()),
    )
    path = tmp_path / "hard.md"
    write_report(report, path)
    text = path.read_text(encoding="utf-8")
    assert "分层" in text
    assert "single-hop" in text
    assert "n/a" in text
    assert "difficulty" in path.with_suffix(".json").read_text(
        encoding="utf-8"
    )


def test_stratum_without_applicable_rows_reports_none():
    report = evaluate(
        _Graph(),
        FakeRetriever([]),
        _golden(),
        FakeRunnable(_judge_result()),
    )
    unanswerable = report.strata["category"]["unanswerable-distractor"]
    assert unanswerable["tool_accuracy"] is None
    assert unanswerable["context_precision"] is None
    assert unanswerable["refusal_rate"] == 0.0
    easy = report.strata["category"]["single-hop"]
    assert easy["tool_accuracy"] == 1.0


class _RefusalGraph:
    def invoke(self, payload, config=None, **kwargs):
        return {
            "messages": [
                AIMessage(content="根据现有资料无法回答。")
            ]
        }


def test_unanswerable_refusal_must_also_be_faithful():
    from eval.judge import JudgeResult

    judge = FakeRunnable(
        JudgeResult(
            correctness=0,
            faithfulness=2,
            citation_support=False,
            reason="refused but added unsupported advice",
        )
    )
    report = evaluate(
        _RefusalGraph(),
        FakeRetriever([]),
        _golden()[1:],
        judge,
    )
    row = report.rows[0]
    assert row["refused"] is True
    assert row["task_success"] is False
    assert report.generation["refusal_rate"] == 1.0


def test_closed_book_uses_correctness_without_citation():
    from eval.judge import JudgeResult

    judge = FakeRunnable(
        JudgeResult(
            correctness=4,
            faithfulness=4,
            citation_support=False,
            reason="closed-book answer correct but uncited",
        )
    )
    report = evaluate(
        _Graph(),
        _ExplodingRetriever(),
        _golden()[:1],
        judge,
        closed_book=True,
    )
    row = report.rows[0]
    assert row["citation_support"] is False
    assert row["task_success"] is True
    assert row["answerable_success"] is True
    assert report.generation["answerable_success"] == 1.0


def test_closed_book_skips_retrieval_and_marks_report():
    report = evaluate(
        _Graph(),
        _ExplodingRetriever(),
        _golden(),
        FakeRunnable(_judge_result()),
        closed_book=True,
    )
    assert report.closed_book is True
    assert report.retrieval == {}
    assert report.rows[0]["retrieved_ids"] == []
    assert report.rows[0]["context_precision"] is None
    assert report.generation["context_precision"] is None
