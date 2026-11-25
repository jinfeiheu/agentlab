"""Analytics 计划执行器测试：并行、依赖、部分失败、并发上限。"""

import asyncio
import time

from agentlab.analytics.budget import Budget
from agentlab.analytics.db import AnalyticsDBError, QueryResult
from agentlab.analytics.executor import cancel_task, execute_plan
from agentlab.analytics.planning import AnalyticsPlan, PlanStep


class _SlowDB:
    """可配置延迟/失败的 fake DB，并记录最大并发。"""

    def __init__(self, delays: dict[str, float], failures=None):
        self.delays = delays
        self.failures = set(failures or ())
        self.active = 0
        self.max_active = 0
        self.calls: list[str] = []

    async def execute(
        self, sql_text, tenant_id, max_rows=200, timeout_ms=5000
    ):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        self.calls.append(sql_text)
        try:
            await asyncio.sleep(self.delays.get(sql_text, 0.01))
            if sql_text in self.failures:
                raise AnalyticsDBError(f"{sql_text} 失败")
            return QueryResult(
                columns=["x"],
                rows=[[sql_text]],
                row_count=1,
                truncated=False,
                duration_ms=1.0,
            )
        finally:
            self.active -= 1


def _plan(*steps: PlanStep) -> AnalyticsPlan:
    return AnalyticsPlan(question="测试问题", steps=list(steps))


def _step(
    step_id: str, sql: str, depends_on: list[str] | None = None
) -> PlanStep:
    return PlanStep(
        id=step_id,
        goal=sql,
        kind="query",
        depends_on=depends_on or [],
        expected_output="单行结果",
    )


async def test_independent_steps_run_in_parallel():
    db = _SlowDB({"q1": 0.2, "q2": 0.2})
    plan = _plan(_step("s1", "q1"), _step("s2", "q2"))
    budget = Budget(max_steps=10, max_concurrency=2)

    started = time.perf_counter()
    result = await execute_plan(
        plan, db, budget, max_concurrency=2
    )
    elapsed = time.perf_counter() - started

    assert result.success is True
    assert db.max_active == 2
    assert elapsed < 0.35


async def test_dependent_steps_run_serially():
    db = _SlowDB({"q1": 0.05, "q2": 0.05})
    plan = _plan(
        _step("s1", "q1"),
        _step("s2", "q2", depends_on=["s1"]),
    )
    budget = Budget(max_steps=10, max_concurrency=2)

    result = await execute_plan(plan, db, budget, max_concurrency=2)

    assert result.success is True
    assert db.max_active == 1
    assert db.calls == ["q1", "q2"]


async def test_partial_failure_returns_partial_results():
    db = _SlowDB({"q1": 0.01, "q2": 0.01}, failures={"q2"})
    plan = _plan(_step("s1", "q1"), _step("s2", "q2"))
    budget = Budget(max_steps=10, max_concurrency=2)

    result = await execute_plan(plan, db, budget, max_concurrency=2)

    assert result.success is False
    assert result.partial is True
    assert result.steps["s1"].status == "success"
    assert result.steps["s2"].status == "error"
    assert result.errors
    assert result.steps["s1"].result["row_count"] == 1


async def test_max_concurrency_queues():
    db = _SlowDB({f"q{i}": 0.05 for i in range(4)})
    plan = _plan(
        *[_step(f"s{i}", f"q{i}") for i in range(4)]
    )
    budget = Budget(max_steps=10, max_concurrency=2)

    result = await execute_plan(plan, db, budget, max_concurrency=2)

    assert result.success is True
    assert db.max_active <= 2
    assert len(db.calls) == 4


class _CancelAfterDB(_SlowDB):
    """在指定 SQL 完成后触发取消。"""

    def __init__(self, delays, cancel_after, request_id):
        super().__init__(delays)
        self.cancel_after = cancel_after
        self.request_id = request_id

    async def execute(
        self, sql_text, tenant_id, max_rows=200, timeout_ms=5000
    ):
        result = await super().execute(
            sql_text, tenant_id, max_rows, timeout_ms
        )
        if sql_text == self.cancel_after:
            cancel_task(self.request_id)
        return result


async def test_cancel_stops_new_steps():
    request_id = "req-cancel"
    db = _CancelAfterDB(
        {"q1": 0.01, "q2": 0.01, "q3": 0.01},
        cancel_after="q1",
        request_id=request_id,
    )
    plan = _plan(
        _step("s1", "q1"),
        _step("s2", "q2", depends_on=["s1"]),
        _step("s3", "q3", depends_on=["s2"]),
    )
    budget = Budget(max_steps=10, max_concurrency=2)

    result = await execute_plan(
        plan,
        db,
        budget,
        max_concurrency=2,
        request_id=request_id,
    )

    assert result.steps["s1"].status == "success"
    assert result.steps["s2"].status == "cancelled"
    assert result.steps["s3"].status == "cancelled"
    assert db.calls == ["q1"]
