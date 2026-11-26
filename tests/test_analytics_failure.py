"""Analytics 混沌测试：超时、DB 故障、审批拒绝、预算与 SSE 断连。"""

import asyncio

import pytest

from agentlab.analytics import graph as graph_module
from agentlab.analytics.db import AnalyticsDBError, QueryResult
from agentlab.analytics.graph import (
    Intent,
    SQLPlan,
    build_analytics_graph,
    run_analytics_question,
)
from agentlab.analytics.reliability import AnalyticsTimeoutError
from agentlab.analytics.session import AnalyticsSessionStore
from agentlab.analytics.versioning import CostBudget
from agentlab.api.analytics import events as analytics_events_module


class ScriptedModel:
    def __init__(self, results):
        self.results = list(results)
        self.index = 0

    def with_structured_output(self, schema, **kwargs):
        return self

    async def ainvoke(self, prompt, **kwargs):
        result = self.results[self.index]
        self.index += 1
        if isinstance(result, Exception):
            raise result
        return result


class SlowModel:
    def with_structured_output(self, schema, **kwargs):
        return self

    async def ainvoke(self, prompt, **kwargs):
        await asyncio.sleep(0.2)


class ChaosDB:
    def __init__(
        self,
        *,
        explain_cost: float = 0.0,
        execute_error: Exception | None = None,
    ):
        self.explain_cost = explain_cost
        self.execute_error = execute_error
        self.queries = []

    async def explain(self, sql_text, tenant_id, timeout_ms=5000):
        return self.explain_cost

    async def execute(
        self, sql_text, tenant_id, max_rows=200, timeout_ms=5000
    ):
        self.queries.append(sql_text)
        if self.execute_error is not None:
            raise self.execute_error
        return QueryResult(
            columns=["x"],
            rows=[[1]],
            row_count=1,
            truncated=False,
            duration_ms=1.0,
        )


@pytest.fixture(autouse=True)
def audit_calls(monkeypatch):
    calls = []

    async def fake(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(
        graph_module, "write_audit", fake, raising=False
    )
    monkeypatch.setattr(
        analytics_events_module, "write_audit", fake, raising=False
    )
    return calls


async def test_model_timeout_is_audited(monkeypatch, audit_calls):
    monkeypatch.setattr(graph_module, "MODEL_TIMEOUT_S", 0.01)
    graph = build_analytics_graph(SlowModel(), ChaosDB())

    with pytest.raises(AnalyticsTimeoutError):
        await run_analytics_question(graph, "查询收入", "tenant_a")

    assert audit_calls[-1]["status"] == "error"


async def test_db_disconnect_degrades_to_readable_failure(audit_calls):
    model = ScriptedModel(
        [
            Intent(intent="answer"),
            SQLPlan(sql="SELECT 1 AS x FROM orders"),
            SQLPlan(sql="SELECT 2 AS x FROM orders"),
            SQLPlan(sql="SELECT 3 AS x FROM orders"),
        ]
    )
    db = ChaosDB(
        execute_error=AnalyticsDBError("connection lost")
    )
    graph = build_analytics_graph(model, db)

    state = await run_analytics_question(graph, "查询订单", "tenant_a")

    assert "修复失败" in state["answer"]
    assert len(db.queries) == 3
    assert audit_calls[-1]["status"] == "error"


async def test_high_cost_without_thread_is_rejected_and_audited(
    audit_calls,
):
    model = ScriptedModel(
        [
            Intent(intent="answer"),
            SQLPlan(sql="SELECT 1 AS x FROM orders"),
        ]
    )
    graph = build_analytics_graph(
        model, ChaosDB(explain_cost=200000)
    )

    state = await run_analytics_question(graph, "查询订单", "tenant_a")

    assert state["rejected"] is True
    assert "人工审批" in state["answer"]
    assert audit_calls[-1]["status"] == "rejected"


async def test_budget_exceeded_is_readable_and_audited(audit_calls):
    model = ScriptedModel(
        [
            Intent(intent="answer"),
            SQLPlan(sql="SELECT 1 AS x FROM orders"),
        ]
    )
    graph = build_analytics_graph(
        model,
        ChaosDB(),
        budget=CostBudget(max_cost=0.001, cost_per_call=0.001),
    )

    state = await run_analytics_question(graph, "查询订单", "tenant_a")

    assert state["budget_exceeded"] is True
    assert "成本预算" in state["answer"]
    assert audit_calls[-1]["status"] == "budget"


class FakeStreamGraph:
    def __init__(self, updates):
        self.updates = updates

    async def astream(self, payload, config=None, stream_mode=None):
        for update in self.updates:
            yield update


class DisconnectingRequest:
    async def is_disconnected(self):
        return True


async def test_sse_disconnect_writes_cancelled_audit(audit_calls):
    graph = FakeStreamGraph(
        [{"understand": {"intent": {"intent": "answer"}}}]
    )
    payload = {
        "question": "查询收入",
        "tenant_id": "tenant_a",
        "request_id": "req-sse",
        "user_id": "user_alice",
    }
    sessions = AnalyticsSessionStore()

    events = [
        event
        async for event in analytics_events_module.analytics_events(
            graph,
            payload,
            {},
            sessions,
            "user_alice",
            "s1",
            DisconnectingRequest(),
        )
    ]

    assert not any('"type": "final"' in event for event in events)
    assert audit_calls[-1]["status"] == "cancelled"


async def test_sse_final_writes_success_audit(audit_calls):
    graph = FakeStreamGraph(
        [
            {"plan_sql": {"sql": "SELECT 1 AS x"}},
            {
                "execute": {
                    "result": {
                        "columns": ["x"],
                        "rows": [[1]],
                        "row_count": 1,
                    }
                }
            },
            {"answer": {"answer": "结果 1", "chart_spec": None}},
        ]
    )
    payload = {
        "question": "查询收入",
        "tenant_id": "tenant_a",
        "request_id": "req-sse-ok",
        "user_id": "user_alice",
    }
    sessions = AnalyticsSessionStore()

    events = [
        event
        async for event in analytics_events_module.analytics_events(
            graph, payload, {}, sessions, "user_alice", "s1"
        )
    ]

    assert any('"type": "final"' in event for event in events)
    assert audit_calls[-1]["status"] == "success"
    assert "查询收入" in sessions.context("user_alice", "s1")
