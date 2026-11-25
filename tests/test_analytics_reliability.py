"""Analytics 可靠性测试：超时、重试、熔断与 repair 上限。"""

import asyncio
import os
import time

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from agentlab.analytics.db import AnalyticsDB, AnalyticsDBError, QueryResult
from agentlab.analytics.graph import (
    AnswerOutput,
    Intent,
    SQLPlan,
    build_analytics_graph,
    run_analytics_question,
)
from agentlab.analytics.reliability import (
    AnalyticsTimeoutError,
    CircuitBreaker,
    retry_async,
    run_with_timeout,
)

TEST_ANALYTICS_DB = os.getenv("TEST_ANALYTICS_DATABASE_URL") or os.getenv(
    "ANALYTICS_DATABASE_URL",
    "postgresql://analytics_reader:analytics_reader@localhost:5432/agentlab",
)

requires_db = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="需要真实 Postgres；设置 RUN_INTEGRATION=1 后运行",
)


@pytest.fixture(autouse=True)
def _stub_audit(monkeypatch):
    """离线测试不写真实审计表。"""
    from agentlab.analytics import graph as graph_module

    async def noop(**kwargs):
        return None

    monkeypatch.setattr(
        graph_module, "write_audit", noop, raising=False
    )


async def test_run_with_timeout_raises_readable_error():
    async def slow():
        await asyncio.sleep(1)

    with pytest.raises(AnalyticsTimeoutError, match="超时"):
        await run_with_timeout(
            slow(), timeout_s=0.01, label="understand"
        )


async def test_run_with_timeout_returns_result():
    async def quick():
        return 42

    assert (
        await run_with_timeout(quick(), timeout_s=1, label="plan_sql")
        == 42
    )


async def test_retry_async_retries_until_success():
    attempts = 0

    async def flaky():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("transient")
        return "ok"

    assert await retry_async(flaky, attempts=3, base_delay=0.0) == "ok"
    assert attempts == 3


async def test_retry_async_raises_after_attempts():
    attempts = 0

    async def always_fail():
        nonlocal attempts
        attempts += 1
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await retry_async(always_fail, attempts=2, base_delay=0.0)
    assert attempts == 2


def test_circuit_breaker_opens_after_threshold():
    now = [0.0]
    breaker = CircuitBreaker(
        failure_threshold=2,
        reset_timeout_s=10,
        clock=lambda: now[0],
    )

    assert breaker.allow_request() is True
    breaker.record_failure()
    assert breaker.allow_request() is True
    breaker.record_failure()
    assert breaker.allow_request() is False

    now[0] = 5.0
    assert breaker.allow_request() is False
    now[0] = 11.0
    assert breaker.allow_request() is True
    breaker.record_success()
    assert breaker.allow_request() is True


def test_circuit_breaker_reopens_after_half_open_failure():
    now = [0.0]
    breaker = CircuitBreaker(
        failure_threshold=2,
        reset_timeout_s=10,
        clock=lambda: now[0],
    )

    breaker.record_failure()
    breaker.record_failure()
    assert breaker.allow_request() is False

    now[0] = 11.0
    assert breaker.allow_request() is True
    breaker.record_failure()
    assert breaker.allow_request() is False


@pytest.mark.integration
@requires_db
async def test_db_timeout_does_not_hang():
    db = AnalyticsDB(TEST_ANALYTICS_DB)
    started = time.perf_counter()

    with pytest.raises(AnalyticsDBError) as exc_info:
        await db.execute(
            "SELECT pg_sleep(2)",
            tenant_id="tenant_a",
            timeout_ms=100,
        )

    elapsed = time.perf_counter() - started
    assert elapsed < 1.5
    assert "timeout" in str(exc_info.value).lower()


class _SequenceModel:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def with_structured_output(self, schema, **kwargs):
        return self

    async def ainvoke(self, prompt, **kwargs):
        result = self.results[self.calls]
        self.calls += 1
        return result


class _AlwaysFailDB:
    async def explain(self, sql_text, tenant_id, timeout_ms=5000):
        return 0.0

    async def execute(self, *args, **kwargs):
        raise AnalyticsDBError("模拟数据库失败")


async def test_graph_stops_after_repair_limit():
    model = _SequenceModel(
        [
            Intent(intent="answer", metrics=["revenue"]),
            SQLPlan(sql="SELECT * FROM orders"),
            SQLPlan(sql="SELECT * FROM orders"),
            SQLPlan(sql="SELECT * FROM orders"),
        ]
    )
    graph = build_analytics_graph(model, _AlwaysFailDB())

    result = await asyncio.wait_for(
        run_analytics_question(graph, "查询订单", "tenant_a"),
        timeout=2,
    )

    assert result["repair_count"] == 2
    assert "SQL 修复失败" in result["answer"]


class _SlowModel:
    def with_structured_output(self, schema, **kwargs):
        return self

    async def ainvoke(self, prompt, **kwargs):
        await asyncio.sleep(0.2)
        return Intent(intent="answer")


class _NoopDB:
    async def explain(self, sql_text, tenant_id, timeout_ms=5000):
        return 0.0

    async def execute(self, *args, **kwargs):
        raise AssertionError("不应执行 SQL")


async def test_graph_model_timeout_is_readable(monkeypatch):
    from agentlab.analytics import graph as graph_module

    monkeypatch.setattr(graph_module, "MODEL_TIMEOUT_S", 0.01)
    graph = build_analytics_graph(_SlowModel(), _NoopDB())

    with pytest.raises(AnalyticsTimeoutError, match="超时"):
        await asyncio.wait_for(
            run_analytics_question(graph, "测试问题", "tenant_a"),
            timeout=2,
        )


def _payload(question: str, tenant_id: str) -> dict:
    return {
        "question": question,
        "tenant_id": tenant_id,
        "request_id": "test-request",
        "user_id": "user_alice",
        "intent": {},
        "clarification": "",
        "sql": "",
        "sql_error": "",
        "repair_count": 0,
        "result": {},
        "answer": "",
        "chart_spec": None,
    }


class _CostDB:
    """返回固定 EXPLAIN 成本，并记录实际执行次数。"""

    def __init__(self, cost: float):
        self.cost = cost
        self.explained = 0
        self.executed = 0
        self.result = QueryResult(
            columns=["x"],
            rows=[[1]],
            row_count=1,
            truncated=False,
            duration_ms=1.0,
        )

    async def explain(self, sql_text, tenant_id, timeout_ms=5000):
        self.explained += 1
        return self.cost

    async def execute(
        self, sql_text, tenant_id, max_rows=200, timeout_ms=5000
    ):
        self.executed += 1
        return self.result


async def test_high_cost_requires_approval_and_can_reject():
    model = _SequenceModel(
        [
            Intent(intent="answer"),
            SQLPlan(sql="SELECT * FROM orders"),
            AnswerOutput(answer="不应执行"),
        ]
    )
    db = _CostDB(cost=200000)
    graph = build_analytics_graph(
        model, db, checkpointer=InMemorySaver()
    )
    config = {"configurable": {"thread_id": "cost-reject"}}

    await graph.ainvoke(_payload("查询订单", "tenant_a"), config)
    assert graph.get_state(config).interrupts
    assert db.executed == 0

    state = await graph.ainvoke(Command(resume="n"), config)
    assert db.executed == 0
    assert "拒绝" in state["answer"]


async def test_high_cost_without_checkpointer_fails_closed():
    model = _SequenceModel(
        [
            Intent(intent="answer"),
            SQLPlan(sql="SELECT * FROM orders"),
        ]
    )
    db = _CostDB(cost=200000)
    graph = build_analytics_graph(model, db)

    state = await graph.ainvoke(_payload("查询订单", "tenant_a"))

    assert db.executed == 0
    assert state.get("rejected") is True
    assert "人工审批" in state["answer"]


async def test_high_cost_can_be_approved():
    model = _SequenceModel(
        [
            Intent(intent="answer"),
            SQLPlan(sql="SELECT * FROM orders"),
            AnswerOutput(answer="执行成功"),
        ]
    )
    db = _CostDB(cost=200000)
    graph = build_analytics_graph(
        model, db, checkpointer=InMemorySaver()
    )
    config = {"configurable": {"thread_id": "cost-approve"}}

    await graph.ainvoke(_payload("查询订单", "tenant_a"), config)
    assert graph.get_state(config).interrupts

    state = await graph.ainvoke(Command(resume="y"), config)
    assert db.executed == 1
    assert state["answer"] == "执行成功"


async def test_low_cost_executes_without_interrupt():
    model = _SequenceModel(
        [
            Intent(intent="answer"),
            SQLPlan(sql="SELECT * FROM orders"),
            AnswerOutput(answer="直接执行"),
        ]
    )
    db = _CostDB(cost=1.0)
    graph = build_analytics_graph(model, db)

    state = await graph.ainvoke(_payload("查询订单", "tenant_a"))

    assert db.explained == 1
    assert db.executed == 1
    assert state["answer"] == "直接执行"
