"""Analytics 评测的离线测试：golden 校验、结果归一化和指标汇总。"""

from pathlib import Path

from eval.run_analytics_eval import (
    actual_outcome,
    compute_metrics,
    load_golden,
    rows_match,
    run_eval,
)

GOLDEN = (
    Path(__file__).resolve().parents[1] / "eval" / "analytics_golden.jsonl"
)


def test_golden_set_size_and_distribution():
    items = load_golden(GOLDEN)
    outcomes = [item["expected_outcome"] for item in items]

    assert len(items) == 20
    assert outcomes.count("answer") == 14
    assert outcomes.count("clarify") == 3
    assert outcomes.count("refuse") == 3
    for item in items:
        assert {
            "question",
            "tenant_id",
            "expected_outcome",
            "expected_result",
            "tags",
        } <= item.keys()
        if item["expected_outcome"] == "answer":
            assert item["expected_columns"]
            assert item["expected_result"]


def test_rows_match_is_order_insensitive_and_tolerant():
    assert rows_match(["x"], [[2.001], [1.0]], ["x"], [[1], [2]]) is True


def test_rows_match_rejects_wrong_value():
    assert rows_match(["x"], [[2]], ["x"], [[1]]) is False


def test_rows_match_aligns_columns_by_name():
    actual_columns = ["order_count", "channel"]
    actual_rows = [[826, "web"], [803, "mobile"]]
    expected_columns = ["channel", "order_count"]
    expected_rows = [["web", 826], ["mobile", 803]]

    assert (
        rows_match(
            actual_columns,
            actual_rows,
            expected_columns,
            expected_rows,
        )
        is True
    )


def test_actual_outcome_classifies():
    assert actual_outcome({"clarification": "请明确时间范围"}) == "clarify"
    assert (
        actual_outcome(
            {"answer": "根据现有数据无法回答该问题。", "result": {}}
        )
        == "refuse"
    )
    assert (
        actual_outcome(
            {
                "answer": "收入为 100",
                "result": {"columns": ["x"], "rows": [[100]]},
            }
        )
        == "answer"
    )
    assert actual_outcome({}) == "error"


def test_compute_metrics():
    records = [
        {
            "expected_outcome": "answer",
            "matched": True,
            "latency_ms": 10,
            "cost_estimate": 0.001,
            "repair_count": 0,
        },
        {
            "expected_outcome": "answer",
            "matched": False,
            "latency_ms": 20,
            "cost_estimate": 0.001,
            "repair_count": 1,
        },
        {
            "expected_outcome": "clarify",
            "matched": True,
            "latency_ms": 30,
            "cost_estimate": 0.001,
            "repair_count": 0,
        },
        {
            "expected_outcome": "refuse",
            "matched": True,
            "latency_ms": 40,
            "cost_estimate": 0.001,
            "repair_count": 0,
        },
    ]

    summary = compute_metrics(records)

    assert summary["count"] == 4
    assert summary["task_success"] == 0.75
    assert summary["execution_accuracy"] == 0.5
    assert summary["clarification_rate"] == 1.0
    assert summary["refusal_rate"] == 1.0
    assert summary["p50_latency_ms"] == 20
    assert summary["p95_latency_ms"] == 40


class FakeGraph:
    """按问题返回 answer/clarify/refuse 三种状态。"""

    async def ainvoke(self, payload, config=None):
        question = payload["question"]
        if "歧义" in question:
            return {
                "question": question,
                "clarification": "请明确时间范围",
                "answer": "",
                "result": {},
            }
        if "不存在" in question:
            return {
                "question": question,
                "clarification": "",
                "answer": "根据现有数据无法回答该问题。",
                "result": {},
            }
        return {
            "question": question,
            "clarification": "",
            "answer": "结果 1",
            "sql": "SELECT 1",
            "repair_count": 0,
            "result": {
                "columns": ["x"],
                "rows": [[1]],
                "row_count": 1,
                "truncated": False,
                "duration_ms": 1.0,
            },
        }


async def test_run_eval_with_fake_graph():
    items = [
        {
            "question": "查询 1",
            "tenant_id": "tenant_a",
            "expected_outcome": "answer",
            "expected_columns": ["x"],
            "expected_result": [[1]],
            "tags": [],
        },
        {
            "question": "歧义问题",
            "tenant_id": "tenant_a",
            "expected_outcome": "clarify",
            "expected_columns": None,
            "expected_result": None,
            "tags": [],
        },
        {
            "question": "不存在的数据",
            "tenant_id": "tenant_a",
            "expected_outcome": "refuse",
            "expected_columns": None,
            "expected_result": None,
            "tags": [],
        },
    ]

    report = await run_eval(items, FakeGraph())

    assert report["summary"]["count"] == 3
    assert report["summary"]["task_success"] == 1.0
    assert report["summary"]["execution_accuracy"] == 1.0
    assert report["summary"]["clarification_rate"] == 1.0
    assert report["summary"]["refusal_rate"] == 1.0
