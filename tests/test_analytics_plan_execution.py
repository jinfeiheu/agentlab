"""多步计划执行接线：SQL-in-plan、逐步骤审计、部分失败与回退。"""

import pytest

from agentlab.analytics import graph as graph_module
from agentlab.analytics.db import AnalyticsDBError, QueryResult
from agentlab.analytics.graph import (
    AnswerOutput,
    Intent,
    SQLPlan,
    build_analytics_graph,
    run_analytics_question,
)
from agentlab.analytics.planning import AnalyticsPlan, PlanStep


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


class ScriptedDB:
    def __init__(self, by_marker=None, fail_marker=None):
        self.by_marker = by_marker or {}
        self.fail_marker = fail_marker
        self.queries = []

    async def explain(self, sql_text, tenant_id, timeout_ms=5000):
        return 0.0

    async def execute(
        self, sql_text, tenant_id, max_rows=200, timeout_ms=5000
    ):
        self.queries.append(sql_text)
        if self.fail_marker and self.fail_marker in sql_text:
            raise AnalyticsDBError("connection lost")
        for marker, response in self.by_marker.items():
            if marker in sql_text:
                return response
        raise AssertionError(f"no response for {sql_text}")


def _result(column="revenue", value=100) -> QueryResult:
    return QueryResult(
        columns=[column],
        rows=[[value]],
        row_count=1,
        truncated=False,
        duration_ms=1.0,
    )


def _step(step_id, column, value, sql):
    return PlanStep(
        id=step_id,
        goal=f"查询 {column}",
        kind="query",
        sql=sql,
        metric_ids=[column],
        expected_output=f"columns: {column}",
    )


def _plan(*steps) -> AnalyticsPlan:
    return AnalyticsPlan(
        question="收入与订单数",
        steps=list(steps),
        max_steps=6,
    )


@pytest.fixture(autouse=True)
def audits(monkeypatch):
    calls = []

    async def audit(**kwargs):
        calls.append(("audit", kwargs))

    async def step_audit(**kwargs):
        calls.append(("step", kwargs))

    monkeypatch.setattr(graph_module, "write_audit", audit, raising=False)
    monkeypatch.setattr(
        graph_module, "write_step_audit", step_audit, raising=False
    )
    return calls


async def test_plan_mode_executes_steps_and_audits_each_one(audits):
    plan = _plan(
        _step(
            "s1",
            "revenue",
            100,
            "SELECT 1 AS revenue FROM orders WHERE tenant_id='tenant_a'",
        ),
        _step(
            "s2",
            "order_count",
            2,
            "SELECT 2 AS order_count FROM orders "
            "WHERE tenant_id='tenant_a'",
        ),
    )
    model = ScriptedModel(
        [
            Intent(intent="answer"),
            plan,
            AnswerOutput(answer="收入 100，订单 2。"),
        ]
    )
    db = ScriptedDB(
        {
            "revenue": _result("revenue", 100),
            "order_count": _result("order_count", 2),
        }
    )
    graph = build_analytics_graph(
        model, db, multi_step=True
    )

    state = await run_analytics_question(
        graph, "收入与订单数", "tenant_a"
    )

    assert state["plan_result"]["success"] is True
    assert len(state["step_audits"]) == 2
    assert all(
        audit["status"] == "success" for audit in state["step_audits"]
    )
    assert state["result"]["columns"] == ["revenue"]
    assert state["agent_steps"] == 2
    assert state["prompt_versions"]["plan"] == "v1"
    step_calls = [call for kind, call in audits if kind == "step"]
    assert len(step_calls) == 2
    assert {call["step_id"] for call in step_calls} == {"s1", "s2"}


async def test_invalid_plan_falls_back_to_single_sql(audits):
    bad = _plan(
        PlanStep(
            id="s1",
            goal="查询收入",
            kind="query",
            expected_output="columns: revenue",
        )
    )
    model = ScriptedModel(
        [
            Intent(intent="answer"),
            bad,
            SQLPlan(
                sql="SELECT 1 AS revenue FROM orders "
                "WHERE tenant_id='tenant_a'"
            ),
            AnswerOutput(answer="回退成功。"),
        ]
    )
    db = ScriptedDB({"revenue": _result("revenue", 1)})
    graph = build_analytics_graph(model, db, multi_step=True)

    state = await run_analytics_question(graph, "收入", "tenant_a")

    assert state["plan_error"]
    assert state["result"]["row_count"] == 1
    assert state["answer"] == "回退成功。"


async def test_duplicate_sql_is_executed_once(audits):
    sql = "SELECT 1 AS revenue FROM orders WHERE tenant_id='tenant_a'"
    plan = _plan(
        _step("s1", "revenue", 100, sql),
        _step("s2", "revenue", 100, sql),
    )
    model = ScriptedModel(
        [
            Intent(intent="answer"),
            plan,
            AnswerOutput(answer="收入 100。"),
        ]
    )
    db = ScriptedDB({"revenue": _result("revenue", 100)})
    graph = build_analytics_graph(model, db, multi_step=True)

    state = await run_analytics_question(graph, "收入", "tenant_a")

    assert len(db.queries) == 1
    assert state["duplicate_queries"] == 1
    assert all(
        audit["status"] == "success" for audit in state["step_audits"]
    )
    assert "重复 SQL" in state["step_audits"][1]["reason"]


async def test_plan_repairs_failed_step_once(audits):
    plan = _plan(
        _step(
            "s1",
            "revenue",
            100,
            "SELECT 1 AS revenue FROM orders "
            "WHERE tenant_id='tenant_a' AND bad_marker='x'",
        )
    )
    model = ScriptedModel(
        [
            Intent(intent="answer"),
            plan,
            SQLPlan(
                sql="SELECT 1 AS revenue FROM orders "
                "WHERE tenant_id='tenant_a'"
            ),
            AnswerOutput(answer="修复后收入 100。"),
        ]
    )
    db = ScriptedDB(
        {"revenue": _result("revenue", 100)},
        fail_marker="bad_marker",
    )
    graph = build_analytics_graph(model, db, multi_step=True)

    state = await run_analytics_question(graph, "收入", "tenant_a")

    assert state["plan_result"]["success"] is True
    assert state["step_audits"][0]["status"] == "success"
    assert "bad_marker" not in state["step_audits"][0]["sql"]
    assert len(db.queries) == 2
    assert state["answer"] == "修复后收入 100。"


async def test_partial_step_failure_keeps_successful_result(audits):
    plan = _plan(
        _step(
            "s1",
            "revenue",
            100,
            "SELECT 1 AS revenue FROM orders WHERE tenant_id='tenant_a'",
        ),
        _step(
            "s2",
            "order_count",
            2,
            "SELECT 2 AS order_count FROM orders "
            "WHERE tenant_id='tenant_a'",
        ),
    )
    model = ScriptedModel(
        [
            Intent(intent="answer"),
            plan,
            SQLPlan(
                sql="SELECT 3 AS order_count FROM orders "
                "WHERE tenant_id='tenant_a'"
            ),
            AnswerOutput(answer="部分结果：收入 100。"),
        ]
    )
    db = ScriptedDB(
        {"revenue": _result("revenue", 100)},
        fail_marker="order_count",
    )
    graph = build_analytics_graph(model, db, multi_step=True)

    state = await run_analytics_question(
        graph, "收入与订单数", "tenant_a"
    )

    statuses = {
        audit["step_id"]: audit["status"]
        for audit in state["step_audits"]
    }
    assert statuses == {"s1": "success", "s2": "error"}
    assert state["plan_result"]["partial"] is True
    assert state["result"]["columns"] == ["revenue"]
    assert state["answer"] == "部分结果：收入 100。"
