"""Analytics 计划表示与计划校验的测试。"""

import pytest

from agentlab.analytics.planning import (
    AnalyticsPlan,
    PlanBudget,
    PlanStep,
    needs_plan_approval,
    plan_question,
    validate_plan,
)

ALLOWED_TOOLS = {"query", "verify", "clarify", "chart"}
ALLOWED_METRICS = {
    "revenue",
    "gmv",
    "refund_rate",
    "active_customers",
    "order_count",
}


class _PlanModel:
    """固定返回一个计划，模拟 planner 的结构化输出。"""

    def __init__(self, plan: AnalyticsPlan):
        self.plan = plan

    def with_structured_output(self, schema, **kwargs):
        return self

    async def ainvoke(self, prompt, **kwargs):
        return self.plan


def _step(
    step_id: str,
    *,
    kind: str = "query",
    metric_ids: list[str] | None = None,
    depends_on: list[str] | None = None,
    expected_output: str = "单值结果",
) -> PlanStep:
    return PlanStep(
        id=step_id,
        goal=f"目标 {step_id}",
        kind=kind,
        depends_on=depends_on or [],
        metric_ids=metric_ids or [],
        expected_output=expected_output,
    )


def _plan(*steps: PlanStep, max_steps: int = 6) -> AnalyticsPlan:
    return AnalyticsPlan(
        question="测试问题", steps=list(steps), max_steps=max_steps
    )


def _validate(plan: AnalyticsPlan, *, max_steps: int = 6):
    return validate_plan(
        plan,
        ALLOWED_TOOLS,
        ALLOWED_METRICS,
        PlanBudget(max_steps=max_steps),
    )


async def test_simple_question_plans_one_step():
    plan = _plan(_step("s1", metric_ids=["revenue"]))
    result = await plan_question(
        _PlanModel(plan), "2026 年 9 月收入", "catalog"
    )

    assert len(result.steps) == 1
    assert result.steps[0].metric_ids == ["revenue"]


async def test_multi_metric_plan_has_dependencies():
    plan = _plan(
        _step("s1", metric_ids=["revenue"]),
        _step("s2", metric_ids=["refund_rate"]),
        _step(
            "s3",
            kind="verify",
            depends_on=["s1", "s2"],
            expected_output="一致性检查",
        ),
    )
    result = await plan_question(
        _PlanModel(plan), "收入与退款率对比", "catalog"
    )

    assert [step.id for step in result.steps] == ["s1", "s2", "s3"]
    assert result.steps[2].depends_on == ["s1", "s2"]
    assert _validate(result).valid is True


def test_validate_plan_rejects_cycle():
    plan = _plan(
        _step("s1", depends_on=["s2"]),
        _step("s2", depends_on=["s1"]),
    )

    result = _validate(plan)

    assert result.valid is False
    assert "环" in result.reason


def test_validate_plan_rejects_unknown_metric():
    plan = _plan(_step("s1", metric_ids=["nps"]))

    result = _validate(plan)

    assert result.valid is False
    assert "指标" in result.reason


def test_validate_plan_rejects_unknown_tool():
    plan = _plan(_step("s1", kind="delete"))

    result = _validate(plan)

    assert result.valid is False
    assert "工具" in result.reason


def test_validate_plan_rejects_over_budget():
    plan = _plan(_step("s1"), _step("s2"), _step("s3"))

    result = _validate(plan, max_steps=2)

    assert result.valid is False
    assert "预算" in result.reason


def test_validate_plan_rejects_duplicate_ids():
    plan = _plan(_step("s1"), _step("s1"))

    result = _validate(plan)

    assert result.valid is False
    assert "重复" in result.reason


def test_validate_plan_rejects_missing_dependency():
    plan = _plan(_step("s1", depends_on=["s9"]))

    result = _validate(plan)

    assert result.valid is False
    assert "依赖" in result.reason


def test_validate_plan_rejects_missing_expected_output():
    plan = _plan(_step("s1", expected_output=""))

    result = _validate(plan)

    assert result.valid is False
    assert "expected_output" in result.reason or "验收" in result.reason


def test_needs_plan_approval_by_steps():
    plan = _plan(*[_step(f"s{i}") for i in range(6)])

    assert (
        needs_plan_approval(plan, max_steps=5, max_cost=100) is True
    )


def test_needs_plan_approval_by_cost():
    plan = _plan(_step("s1"))

    assert (
        needs_plan_approval(
            plan, max_steps=5, max_cost=100, estimated_cost=200
        )
        is True
    )
