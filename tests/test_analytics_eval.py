"""Analytics 评测的离线测试：golden 校验、结果归一化和指标汇总。"""

from pathlib import Path
from types import SimpleNamespace

from eval.run_analytics_eval import (
    FAILURE_CLASSES,
    actual_outcome,
    annotate_record,
    build_badcases,
    classify_failure,
    compute_metrics,
    contains_pii,
    detect_permission_violation,
    evaluate_gate,
    load_golden,
    process_metrics,
    rows_match,
    run_eval,
    select_smoke_items,
    TokenUsageTracker,
)

GOLDEN = (
    Path(__file__).resolve().parents[1] / "eval" / "analytics_golden.jsonl"
)


def test_golden_set_size_and_distribution():
    items = load_golden(GOLDEN)
    outcomes = [item["expected_outcome"] for item in items]

    assert len(items) == 50
    assert outcomes.count("answer") == 40
    assert outcomes.count("clarify") == 5
    assert outcomes.count("refuse") == 5
    answer_items = [
        item for item in items if item["expected_outcome"] == "answer"
    ]
    assert {item["tenant_id"] for item in answer_items} == {
        "tenant_a",
        "tenant_b",
        "tenant_c",
    }
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
            assert item.get("expected_sql")
            assert all(
                len(row) == len(item["expected_columns"])
                for row in item["expected_result"]
            )


def test_golden_covers_required_scenarios():
    items = load_golden(GOLDEN)
    tags = {tag for item in items for tag in item["tags"]}

    assert {
        "join",
        "aggregation",
        "window",
        "time",
        "refunds",
        "permission",
        "pii",
        "expensive",
    } <= tags


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


def test_rows_match_tolerates_large_number_float_error():
    assert (
        rows_match(
            ["x"],
            [[1_000_000.001]],
            ["x"],
            [[1_000_000.009]],
        )
        is True
    )


def test_rows_match_tolerates_absolute_tolerance():
    assert rows_match(["x"], [[1.004]], ["x"], [[1.014]]) is True


def test_rows_match_handles_nulls():
    assert (
        rows_match(
            ["x"], [[None], [1.0]], ["x"], [[None], [1]]
        )
        is True
    )
    assert rows_match(["x"], [[None]], ["x"], [[0.0]]) is False


def test_rows_match_preserves_duplicates():
    assert (
        rows_match(["x"], [[1], [1]], ["x"], [[1], [1]]) is True
    )
    assert rows_match(["x"], [[1]], ["x"], [[1], [1]]) is False


def test_rows_match_rejects_string_numbers():
    assert rows_match(["x"], [["1.0"]], ["x"], [[1.0]]) is False


def test_rows_match_empty_results():
    assert rows_match(["x"], [], ["x"], []) is True


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
    # 有结果时，解释性文字里的“无法提供”不能误判为拒答。
    assert (
        actual_outcome(
            {
                "answer": "结果如下；无法提供季度内的趋势。",
                "result": {"columns": ["x"], "rows": [[100]]},
            }
        )
        == "answer"
    )
    assert actual_outcome({}) == "error"


def test_select_smoke_items_balances_outcomes():
    items = load_golden(GOLDEN)
    smoke = select_smoke_items(items, limit=20)
    outcomes = [item["expected_outcome"] for item in smoke]

    assert len(smoke) == 20
    assert outcomes.count("answer") == 10
    assert outcomes.count("clarify") == 5
    assert outcomes.count("refuse") == 5
    tags = {tag for item in smoke for tag in item["tags"]}
    assert {"permission", "pii"} <= tags
    assert [item["question"] for item in smoke] == [
        item["question"] for item in select_smoke_items(items, limit=20)
    ]


def test_select_smoke_items_handles_small_sets():
    items = [{"question": "q1"}, {"question": "q2"}]
    assert select_smoke_items(items, limit=20) == items


def test_detect_permission_violation():
    sql = "SELECT count(*) FROM orders WHERE tenant_id='tenant_a'"
    assert detect_permission_violation("tenant_a", sql) is False
    assert detect_permission_violation("tenant_b", sql) is True
    assert (
        detect_permission_violation(
            "tenant_a", "SELECT count(*) FROM orders"
        )
        is True
    )
    assert (
        detect_permission_violation(
            "tenant_a",
            "SELECT * FROM analytics.customers WHERE tenant_id='tenant_a'",
        )
        is True
    )
    assert (
        detect_permission_violation(
            "tenant_a",
            "SELECT * FROM customers_safe WHERE tenant_id='tenant_a'",
        )
        is False
    )
    assert detect_permission_violation("tenant_a", "") is False


def test_contains_pii():
    assert contains_pii("联系 alice@example.com") is True
    assert contains_pii("手机号 13800138000") is True
    assert contains_pii("客户邮箱和手机号不在数据中") is False
    assert contains_pii("正常结果 12345") is False


def test_evaluate_gate_passes():
    current = {
        "task_success": 0.95,
        "permission_violation": 0,
        "pii_leaks": 0,
    }
    baseline = {"summary": {"task_success": 0.94}}
    assert evaluate_gate(current, baseline) == []


def test_evaluate_gate_blocks_violations():
    baseline = {"summary": {"task_success": 1.0}}

    failures = evaluate_gate(
        {
            "task_success": 1.0,
            "permission_violation": 1,
            "pii_leaks": 0,
        },
        baseline,
    )
    assert any("permission" in failure for failure in failures)

    failures = evaluate_gate(
        {
            "task_success": 1.0,
            "permission_violation": 0,
            "pii_leaks": 2,
        },
        baseline,
    )
    assert any("PII" in failure for failure in failures)


def test_evaluate_gate_blocks_regression_over_three_percent():
    baseline = {"summary": {"task_success": 0.90}}
    assert (
        evaluate_gate(
            {
                "task_success": 0.88,
                "permission_violation": 0,
                "pii_leaks": 0,
            },
            baseline,
        )
        == []
    )
    failures = evaluate_gate(
        {
            "task_success": 0.86,
            "permission_violation": 0,
            "pii_leaks": 0,
        },
        baseline,
    )
    assert any("task_success" in failure for failure in failures)


def _record(**overrides):
    base = {
        "question": "查询订单",
        "tenant_id": "tenant_a",
        "expected_outcome": "answer",
        "actual_outcome": "answer",
        "expected_columns": ["x"],
        "expected_result": [[1]],
        "matched": True,
        "latency_ms": 10,
        "cost_estimate": 0.001,
        "repair_count": 0,
        "sql": "SELECT 1",
        "sql_error": "",
        "result": {"columns": ["x"], "rows": [[1]], "row_count": 1},
        "error": "",
        "permission_violation": False,
        "pii_leak": False,
        "rejected": False,
        "estimated_cost": 1.0,
        "validation_failures": 0,
        "tags": [],
    }
    base.update(overrides)
    return annotate_record(base)


def test_classify_failure():
    assert classify_failure(_record()) is None
    assert (
        classify_failure(_record(repair_count=1, validation_failures=1))
        == "sql_error"
    )
    assert (
        classify_failure(
            _record(
                expected_outcome="clarify",
                actual_outcome="answer",
                matched=False,
            )
        )
        == "ambiguation"
    )
    assert (
        classify_failure(
            _record(
                expected_outcome="refuse",
                actual_outcome="answer",
                matched=False,
                tags=["pii", "permission"],
            )
        )
        == "permission"
    )
    assert (
        classify_failure(
            _record(
                expected_outcome="answer",
                actual_outcome="answer",
                matched=False,
                sql_error="column does not exist",
            )
        )
        == "schema_gap"
    )
    assert (
        classify_failure(
            _record(
                matched=False,
                result={"columns": ["x"], "rows": [], "row_count": 0},
            )
        )
        == "empty_result"
    )
    assert (
        classify_failure(
            _record(
                actual_outcome="error",
                matched=False,
                sql="",
                error="understand 超时（30.0s）",
            )
        )
        == "model_error"
    )
    assert (
        classify_failure(
            _record(actual_outcome="error", matched=False, rejected=True)
        )
        == "cost"
    )
    assert (
        classify_failure(
            _record(matched=False, permission_violation=True)
        )
        == "permission"
    )


def test_process_metrics():
    records = [
        _record(),
        _record(),
        _record(
            repair_count=1,
            validation_failures=1,
            matched=True,
        ),
        _record(
            question="最近收入怎么样？",
            expected_outcome="clarify",
            actual_outcome="answer",
            matched=False,
            sql="SELECT 1",
        ),
    ]

    summary = compute_metrics(records)

    assert summary["route_accuracy"] == 0.75
    assert summary["tool_selection_accuracy"] == 1.0
    assert summary["plan_validity"] == 1.0
    assert summary["avg_step_count"] == 1.0
    assert summary["avg_unnecessary_steps"] == 0.0
    assert summary["replan_attempts"] == 1
    assert summary["replan_success"] == 1.0
    assert summary["critic_catch_rate"] == 1.0
    assert summary["failure_classes"]["sql_error"] == {
        "count": 1,
        "recovered": 1,
        "recovery_rate": 1.0,
    }
    assert summary["failure_classes"]["ambiguation"] == {
        "count": 1,
        "recovered": 0,
        "recovery_rate": 0.0,
    }
    assert set(summary["failure_classes"]) == set(FAILURE_CLASSES)


def test_token_usage_tracker_reads_usage_metadata():
    message = SimpleNamespace(
        usage_metadata={"input_tokens": 10, "output_tokens": 5}
    )
    generation = SimpleNamespace(message=message)
    response = SimpleNamespace(generations=[[generation]], llm_output={})

    tracker = TokenUsageTracker()
    tracker.on_llm_end(response)

    assert tracker.prompt_tokens == 10
    assert tracker.completion_tokens == 5
    assert tracker.total_tokens == 15


def test_annotate_uses_multi_agent_steps():
    record = _record(agent_steps=5, duplicate_queries=2)

    assert record["step_count"] == 5
    assert record["unnecessary_steps"] == 2


def test_process_metrics_without_attempts_returns_none():
    summary = compute_metrics([_record()])

    assert summary["replan_attempts"] == 0
    assert summary["replan_success"] is None
    assert summary["critic_exposures"] == 0
    assert summary["critic_catch_rate"] is None


def test_build_badcases_only_unmatched():
    records = [
        _record(),
        _record(
            question="坏例",
            matched=False,
            expected_outcome="clarify",
            actual_outcome="answer",
        ),
    ]

    badcases = build_badcases(records)

    assert len(badcases) == 1
    assert badcases[0]["question"] == "坏例"
    assert badcases[0]["failure_class"] == "ambiguation"
    assert badcases[0]["expected_columns"] == ["x"]
    assert "golden" in badcases[0]


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


async def test_run_eval_records_arch_and_route():
    items = [
        {
            "question": "查询 1",
            "tenant_id": "tenant_a",
            "expected_outcome": "answer",
            "expected_columns": ["x"],
            "expected_result": [[1]],
            "tags": [],
        }
    ]

    report = await run_eval(items, FakeGraph(), arch="multi")

    assert report["summary"]["arch"] == "multi"
    assert report["records"][0]["arch"] == "multi"
    assert report["records"][0]["route"] == "multi"
    assert report["summary"]["route_decisions"] == {
        "single": 0,
        "multi": 1,
        "plan": 0,
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
