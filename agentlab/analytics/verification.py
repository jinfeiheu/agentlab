"""步骤验收、失败分类与重规划。"""

import re
from dataclasses import dataclass
from enum import Enum

from agentlab.analytics.planning import (
    AnalyticsPlan,
    PlanBudget,
    PlanStep,
)

MAX_REPLANS = 2

_MAX_ROWS_RE = re.compile(r"max_rows\s*=\s*(\d+)")
_COLUMNS_RE = re.compile(r"(?:columns|列)\s*[:：]\s*(.+)")


class FailureClass(str, Enum):
    """失败分类，用于决定 repair / replan / clarify / refuse。"""

    AMBIGUATION = "ambiguation"
    SCHEMA_GAP = "schema_gap"
    METRIC_CONFLICT = "metric_conflict"
    SQL_ERROR = "sql_error"
    EMPTY_RESULT = "empty_result"
    TOO_MANY_ROWS = "too_many_rows"
    ANOMALY = "anomaly"
    PERMISSION = "permission"
    COST = "cost"
    MODEL_ERROR = "model_error"
    TOOL_ERROR = "tool_error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class StepVerdict:
    """单步验收结果。"""

    passed: bool
    failure_class: FailureClass | None = None
    reason: str = ""


@dataclass(frozen=True)
class ReplanResult:
    """重规划结果；stopped=True 时 plan 为 None。"""

    plan: AnalyticsPlan | None
    stopped: bool
    reason: str
    replan_count: int


def classify_failure(error, result) -> FailureClass:
    """把错误/结果归类，供恢复策略选择。"""
    text = str(error or "").lower()
    if any(
        marker in text
        for marker in ("permission", "权限", "denied", "rls")
    ):
        return FailureClass.PERMISSION
    if any(
        marker in text
        for marker in (
            "statement timeout",
            "cost",
            "预算",
            "exceeded",
        )
    ):
        return FailureClass.COST
    if any(marker in text for marker in ("timeout", "模型")):
        return FailureClass.MODEL_ERROR
    if any(
        marker in text
        for marker in ("syntax", "does not exist", "undefined", "sql")
    ):
        return FailureClass.SQL_ERROR

    result = result or {}
    if result.get("metric_conflicts"):
        return FailureClass.METRIC_CONFLICT
    if result.get("anomalies"):
        return FailureClass.ANOMALY
    if not result.get("rows"):
        return FailureClass.EMPTY_RESULT
    return FailureClass.UNKNOWN


def verify_step(step: PlanStep, result: dict) -> StepVerdict:
    """按 expected_output 验收单步结果。"""
    result = result or {}

    error = result.get("error")
    if error:
        return StepVerdict(
            False, classify_failure(error, result), str(error)
        )

    conflicts = result.get("metric_conflicts") or []
    if conflicts:
        return StepVerdict(
            False,
            FailureClass.METRIC_CONFLICT,
            "; ".join(str(item) for item in conflicts),
        )

    anomalies = result.get("anomalies") or []
    if anomalies:
        return StepVerdict(
            False,
            FailureClass.ANOMALY,
            "; ".join(str(item) for item in anomalies),
        )

    rows = result.get("rows") or []
    if not rows:
        return StepVerdict(
            False, FailureClass.EMPTY_RESULT, "结果为空"
        )

    expected = step.expected_output or ""
    row_count = int(result.get("row_count", len(rows)))
    max_rows_match = _MAX_ROWS_RE.search(expected)
    if max_rows_match and row_count > int(max_rows_match.group(1)):
        return StepVerdict(
            False,
            FailureClass.TOO_MANY_ROWS,
            f"行数 {row_count} 超过 {max_rows_match.group(1)}",
        )

    columns_match = _COLUMNS_RE.search(expected)
    if columns_match:
        required = [
            column.strip()
            for column in columns_match.group(1).split(",")
            if column.strip()
        ]
        actual = {str(column) for column in result.get("columns", [])}
        missing = [column for column in required if column not in actual]
        if missing:
            return StepVerdict(
                False,
                FailureClass.SCHEMA_GAP,
                f"缺少列：{', '.join(missing)}",
            )

    if expected.strip() == "单值":
        if len(rows) != 1 or len(rows[0]) != 1:
            return StepVerdict(
                False, FailureClass.SCHEMA_GAP, "期望单值结果"
            )

    return StepVerdict(True, None, "")


def replan(
    plan: AnalyticsPlan,
    completed_ids: set[str],
    *,
    previous_completed: set[str] | None = None,
    replan_count: int = 0,
    budget: PlanBudget | None = None,
    failed_step_id: str | None = None,
) -> ReplanResult:
    """只重排未完成步骤；无进展/重复/超预算时终止。"""
    if replan_count >= MAX_REPLANS:
        return ReplanResult(
            None, True, "超过最大重规划次数", replan_count
        )

    if (
        previous_completed is not None
        and completed_ids <= set(previous_completed)
    ):
        return ReplanResult(None, True, "重规划无进展", replan_count)

    if budget is not None and len(plan.steps) > budget.max_steps:
        return ReplanResult(
            None,
            True,
            f"超过预算：{len(plan.steps)} 步 > {budget.max_steps}",
            replan_count,
        )

    ids = [step.id for step in plan.steps]
    if len(set(ids)) != len(ids):
        return ReplanResult(
            None, True, "存在重复步骤", replan_count
        )

    pending = [
        step for step in plan.steps if step.id not in completed_ids
    ]
    if not pending:
        return ReplanResult(
            None, True, "没有待执行步骤", replan_count
        )

    new_plan = plan.model_copy(update={"steps": pending})
    return ReplanResult(new_plan, False, "", replan_count + 1)
