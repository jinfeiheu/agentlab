"""计划执行：依赖调度、并行 fan-out/fan-in、部分失败、预算与取消。"""

import asyncio
import time
from dataclasses import dataclass

from agentlab.analytics.budget import Budget
from agentlab.analytics.planning import AnalyticsPlan, PlanStep

_CANCELLED: set[str] = set()


def cancel_task(request_id: str) -> None:
    """标记任务取消；执行器在每个调度层检查。"""
    _CANCELLED.add(request_id)


def is_cancelled(request_id: str | None) -> bool:
    return bool(request_id and request_id in _CANCELLED)


def clear_cancelled(request_id: str) -> None:
    _CANCELLED.discard(request_id)


@dataclass(frozen=True)
class StepResult:
    """单步执行结果；success / error / skipped / cancelled。"""

    step_id: str
    status: str
    result: dict | None = None
    error: str | None = None
    duration_ms: float = 0.0


@dataclass(frozen=True)
class PlanResult:
    """整体执行结果；partial 表示有成功也有失败/取消。"""

    steps: dict[str, StepResult]
    success: bool
    partial: bool
    errors: list[str]
    duration_ms: float


async def execute_plan(
    plan: AnalyticsPlan,
    db,
    budget: Budget,
    max_concurrency: int = 3,
    tenant_id: str = "tenant_a",
    request_id: str | None = None,
) -> PlanResult:
    """按 depends_on 调度步骤；独立步骤并行，部分失败保留其他结果。"""
    started = time.perf_counter()
    steps = {step.id: step for step in plan.steps}
    completed: dict[str, StepResult] = {}
    remaining = set(steps)
    limit = max(1, min(max_concurrency, budget.max_concurrency))
    semaphore = asyncio.Semaphore(limit)

    async def run_step(step: PlanStep) -> StepResult:
        step_started = time.perf_counter()
        async with semaphore:
            if is_cancelled(request_id):
                return StepResult(step.id, "cancelled", error="任务已取消")
            if budget.exhausted():
                return StepResult(step.id, "skipped", error="预算耗尽")
            budget.consume(steps=1)
            try:
                result = await db.execute(
                    step.sql or step.goal,
                    tenant_id,
                    max_rows=200,
                    timeout_ms=5000,
                )
            except Exception as exc:  # noqa: BLE001 - 单步失败不丢整体结果
                return StepResult(
                    step.id,
                    "error",
                    error=str(exc),
                    duration_ms=(time.perf_counter() - step_started) * 1000,
                )
            payload = {
                "columns": result.columns,
                "rows": result.rows,
                "row_count": result.row_count,
                "truncated": result.truncated,
                "duration_ms": result.duration_ms,
            }
            return StepResult(
                step.id,
                "success",
                result=payload,
                duration_ms=(time.perf_counter() - step_started) * 1000,
            )

    while remaining:
        if is_cancelled(request_id):
            for step_id in list(remaining):
                completed[step_id] = StepResult(
                    step_id, "cancelled", error="任务已取消"
                )
            break

        ready = [
            steps[step_id]
            for step_id in remaining
            if all(
                dep in completed
                for dep in steps[step_id].depends_on
            )
        ]
        if not ready:
            for step_id in list(remaining):
                completed[step_id] = StepResult(
                    step_id, "skipped", error="依赖未满足"
                )
            break

        tasks = [asyncio.create_task(run_step(step)) for step in ready]
        for task in asyncio.as_completed(tasks):
            result = await task
            completed[result.step_id] = result
            remaining.discard(result.step_id)

    duration_ms = (time.perf_counter() - started) * 1000
    errors = [
        result.error
        for result in completed.values()
        if result.error
    ]
    success = bool(completed) and all(
        result.status == "success" for result in completed.values()
    )
    partial = any(
        result.status == "success" for result in completed.values()
    ) and any(
        result.status != "success" for result in completed.values()
    )
    return PlanResult(
        steps=completed,
        success=success,
        partial=partial,
        errors=errors,
        duration_ms=duration_ms,
    )
