"""Analytics Graph 的离线测试：用脚本模型和 Fake DB 验证主流程。"""

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


class ScriptedAnalyticsModel:
    """按调用顺序返回结构化结果，模拟 understand/plan/repair/answer。"""

    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def with_structured_output(self, schema, **kwargs):
        return self

    async def ainvoke(self, prompt, **kwargs):
        result = self.results[self.calls]
        self.calls += 1
        if isinstance(result, Exception):
            raise result
        return result


class FakeAnalyticsDB:
    """返回预设结果或异常，并记录实际执行的 SQL。"""

    def __init__(self, responses):
        self.responses = list(responses)
        self.queries = []

    async def execute(
        self, sql_text, tenant_id, max_rows=200, timeout_ms=5000
    ):
        self.queries.append((sql_text, tenant_id))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def explain(self, sql_text, tenant_id, timeout_ms=5000):
        return 0.0


def _query_result() -> QueryResult:
    return QueryResult(
        columns=["revenue"],
        rows=[(100,)],
        row_count=1,
        truncated=False,
        duration_ms=1.0,
    )


async def test_graph_answers_normal_question():
    model = ScriptedAnalyticsModel(
        [
            Intent(intent="answer", metrics=["revenue"], time_range="上个月"),
            SQLPlan(
                sql="SELECT SUM(oi.quantity * oi.unit_price) AS revenue "
                "FROM order_items oi"
            ),
            AnswerOutput(answer="上月收入为 100 元。"),
        ]
    )
    db = FakeAnalyticsDB([_query_result()])
    graph = build_analytics_graph(model, db)

    result = await run_analytics_question(graph, "上个月收入", "tenant_a")

    assert "100" in result["answer"]
    assert result["sql"]
    assert result["result"]["row_count"] == 1
    assert len(db.queries) == 1
    assert db.queries[0][1] == "tenant_a"


async def test_graph_keeps_result_when_answer_parsing_fails():
    model = ScriptedAnalyticsModel(
        [
            Intent(intent="answer", metrics=["revenue"]),
            SQLPlan(
                sql="SELECT SUM(oi.quantity * oi.unit_price) AS revenue "
                "FROM order_items oi"
            ),
            RuntimeError("AnswerOutput 解析失败"),
        ]
    )
    db = FakeAnalyticsDB([_query_result()])
    graph = build_analytics_graph(model, db)

    result = await run_analytics_question(graph, "上个月收入", "tenant_a")

    assert result["result"]["row_count"] == 1
    assert "100" in result["answer"]


async def test_graph_clarifies_ambiguous_question():
    model = ScriptedAnalyticsModel(
        [
            Intent(
                intent="clarify",
                ambiguous=True,
                clarification="请明确时间范围和收入口径。",
            )
        ]
    )
    db = FakeAnalyticsDB([])
    graph = build_analytics_graph(model, db)

    result = await run_analytics_question(graph, "最近收入怎么样", "tenant_a")

    assert result["clarification"]
    assert "时间范围" in result["clarification"]
    assert db.queries == []


async def test_graph_refuses_unanswerable_question():
    model = ScriptedAnalyticsModel(
        [Intent(intent="refuse", metrics=["nps"])]
    )
    db = FakeAnalyticsDB([])
    graph = build_analytics_graph(model, db)

    result = await run_analytics_question(graph, "NPS 是多少", "tenant_a")

    assert "无法" in result["answer"]
    assert db.queries == []


async def test_graph_repairs_sql_once():
    model = ScriptedAnalyticsModel(
        [
            Intent(intent="answer", metrics=["revenue"]),
            SQLPlan(sql="SELECT * FROM orders"),
            SQLPlan(sql="SELECT * FROM orders LIMIT 10"),
            AnswerOutput(answer="修复后查询成功，共 1 行。"),
        ]
    )
    db = FakeAnalyticsDB(
        [
            AnalyticsDBError("column does not exist"),
            _query_result(),
        ]
    )
    graph = build_analytics_graph(model, db)

    result = await run_analytics_question(graph, "查询订单", "tenant_a")

    assert result["repair_count"] == 1
    assert len(db.queries) == 2
    assert "LIMIT 10" in result["sql"]
    assert "成功" in result["answer"]


@pytest.fixture(autouse=True)
def _stub_audit(monkeypatch):
    """默认不写真实审计表；审计测试会覆盖这个 stub。"""

    async def noop(**kwargs):
        return None

    monkeypatch.setattr(
        graph_module, "write_audit", noop, raising=False
    )


@pytest.fixture
def audit_calls(monkeypatch):
    calls = []

    async def fake(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(
        graph_module, "write_audit", fake, raising=False
    )
    return calls


async def test_graph_writes_audit_on_success(audit_calls):
    model = ScriptedAnalyticsModel(
        [
            Intent(intent="answer", metrics=["revenue"]),
            SQLPlan(sql="SELECT * FROM orders"),
            AnswerOutput(answer="查询成功。"),
        ]
    )
    db = FakeAnalyticsDB([_query_result()])
    graph = build_analytics_graph(model, db)

    result = await run_analytics_question(
        graph, "查询订单", "tenant_a", user_id="user_alice"
    )

    assert len(audit_calls) == 1
    call = audit_calls[0]
    assert call["status"] == "success"
    assert call["request_id"] == result["request_id"]
    assert call["user_id"] == "user_alice"
    assert call["tenant_id"] == "tenant_a"
    assert call["row_count"] == 1
    assert "understand=v1" in call["prompt_version"]
    assert "understand=default" in call["model_id"]


async def test_graph_writes_audit_on_clarify(audit_calls):
    model = ScriptedAnalyticsModel(
        [
            Intent(
                intent="clarify",
                ambiguous=True,
                clarification="请明确时间范围。",
            )
        ]
    )
    db = FakeAnalyticsDB([])
    graph = build_analytics_graph(model, db)

    result = await run_analytics_question(
        graph, "最近收入怎么样", "tenant_a", user_id="user_alice"
    )

    assert len(audit_calls) == 1
    assert audit_calls[0]["status"] == "clarify"
    assert audit_calls[0]["sql"] == ""
    assert audit_calls[0]["request_id"] == result["request_id"]


async def test_graph_writes_audit_on_refuse(audit_calls):
    model = ScriptedAnalyticsModel(
        [Intent(intent="refuse", metrics=["nps"])]
    )
    db = FakeAnalyticsDB([])
    graph = build_analytics_graph(model, db)

    result = await run_analytics_question(
        graph, "NPS 是多少", "tenant_a", user_id="user_alice"
    )

    assert len(audit_calls) == 1
    assert audit_calls[0]["status"] == "refuse"
    assert audit_calls[0]["request_id"] == result["request_id"]


async def test_graph_writes_audit_on_error(audit_calls):
    model = ScriptedAnalyticsModel(
        [
            Intent(intent="answer", metrics=["revenue"]),
            SQLPlan(sql="SELECT * FROM orders"),
            SQLPlan(sql="SELECT * FROM orders"),
            SQLPlan(sql="SELECT * FROM orders"),
        ]
    )
    db = FakeAnalyticsDB(
        [AnalyticsDBError("boom")] * 3
    )
    graph = build_analytics_graph(model, db)

    result = await run_analytics_question(
        graph, "查询订单", "tenant_a", user_id="user_alice"
    )

    assert len(audit_calls) == 1
    assert audit_calls[0]["status"] == "error"
    assert audit_calls[0]["row_count"] == 0
    assert audit_calls[0]["request_id"] == result["request_id"]
