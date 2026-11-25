"""Analytics 验证、失败分类与重规划测试。"""

from agentlab.analytics.planning import PlanBudget, PlanStep
from agentlab.analytics.verification import (
    FailureClass,
    classify_failure,
    replan,
    verify_step,
)


def _step(
    step_id: str = "s1", expected_output: str = "columns: revenue"
) -> PlanStep:
    return PlanStep(
        id=step_id,
        goal="查询收入",
        kind="query",
        metric_ids=["revenue"],
        expected_output=expected_output,
    )


def _result(
    columns=("revenue",),
    rows=((1,),),
    row_count: int | None = None,
    **extra,
) -> dict:
    data = {
        "columns": list(columns),
        "rows": [list(row) for row in rows],
        "row_count": len(rows) if row_count is None else row_count,
    }
    data.update(extra)
    return data


def _plan(*steps: PlanStep):
    from agentlab.analytics.planning import AnalyticsPlan

    return AnalyticsPlan(question="测试问题", steps=list(steps))


def test_verify_step_passes_valid_result():
    verdict = verify_step(_step(), _result())

    assert verdict.passed is True
    assert verdict.failure_class is None


def test_verify_step_classifies_empty_result():
    verdict = verify_step(
        _step(), _result(rows=(), row_count=0)
    )

    assert verdict.passed is False
    assert verdict.failure_class == FailureClass.EMPTY_RESULT


def test_verify_step_classifies_too_many_rows():
    step = _step(expected_output="max_rows=10")
    rows = tuple((index,) for index in range(50))

    verdict = verify_step(step, _result(rows=rows, row_count=50))

    assert verdict.passed is False
    assert verdict.failure_class == FailureClass.TOO_MANY_ROWS


def test_verify_step_classifies_missing_column():
    step = _step(expected_output="columns: revenue, refund_rate")

    verdict = verify_step(step, _result(columns=("revenue",)))

    assert verdict.passed is False
    assert verdict.failure_class == FailureClass.SCHEMA_GAP


def test_verify_step_classifies_metric_conflict():
    result = _result(metric_conflicts=["revenue 与 gmv 口径冲突"])

    verdict = verify_step(_step(), result)

    assert verdict.passed is False
    assert verdict.failure_class == FailureClass.METRIC_CONFLICT


def test_verify_step_classifies_anomaly():
    result = _result(anomalies=["收入为负数"])

    verdict = verify_step(_step(), result)

    assert verdict.passed is False
    assert verdict.failure_class == FailureClass.ANOMALY


def test_verify_step_single_value_shape():
    assert verify_step(
        _step(expected_output="单值"), _result()
    ).passed is True
    assert (
        verify_step(
            _step(expected_output="单值"),
            _result(columns=("revenue", "gmv"), rows=((1, 2),)),
        ).failure_class
        == FailureClass.SCHEMA_GAP
    )


def test_classify_failure_permission():
    assert (
        classify_failure("permission denied for table orders", {})
        == FailureClass.PERMISSION
    )


def test_classify_failure_sql_error():
    assert (
        classify_failure('column "x" does not exist', {})
        == FailureClass.SQL_ERROR
    )


def test_classify_failure_cost():
    assert (
        classify_failure("statement timeout", {})
        == FailureClass.COST
    )


def test_replan_keeps_only_incomplete_steps():
    plan = _plan(_step("s1"), _step("s2"), _step("s3"))

    result = replan(plan, completed_ids={"s1"})

    assert result.stopped is False
    assert result.plan is not None
    assert [step.id for step in result.plan.steps] == ["s2", "s3"]
    assert result.replan_count == 1


def test_replan_stops_without_progress():
    plan = _plan(_step("s1"), _step("s2"))

    result = replan(
        plan,
        completed_ids={"s1"},
        previous_completed={"s1"},
    )

    assert result.stopped is True
    assert "进展" in result.reason


def test_replan_stops_after_max_replans():
    plan = _plan(_step("s1"), _step("s2"))

    result = replan(plan, completed_ids={"s1"}, replan_count=2)

    assert result.stopped is True
    assert "重规划" in result.reason


def test_replan_stops_over_budget():
    plan = _plan(_step("s1"), _step("s2"), _step("s3"))

    result = replan(
        plan,
        completed_ids=set(),
        budget=PlanBudget(max_steps=1),
    )

    assert result.stopped is True
    assert "预算" in result.reason


def test_replan_stops_on_duplicate_steps():
    plan = _plan(_step("s1"), _step("s1"))

    result = replan(plan, completed_ids=set())

    assert result.stopped is True
    assert "重复" in result.reason
