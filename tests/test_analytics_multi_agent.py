"""多 Agent 拓扑、handoff 协议与失败回环测试。"""

from agentlab.analytics.db import QueryResult
from agentlab.analytics.graph import AnswerOutput, Intent, SQLPlan
from agentlab.analytics.multi_agent import (
    MAX_STEPS,
    Critique,
    build_multi_agent_analytics_graph,
)


class ScriptedModel:
    """按调用顺序返回结构化结果，并记录请求的 schema。"""

    def __init__(self, results, forbidden=()):
        self.results = list(results)
        self.forbidden = set(forbidden)
        self.schemas = []
        self._schema = None

    def with_structured_output(self, schema, **kwargs):
        self._schema = schema
        return self

    async def ainvoke(self, prompt, **kwargs):
        self.schemas.append(self._schema)
        if self._schema in self.forbidden:
            raise AssertionError(f"不应调用 {self._schema}")
        return self.results.pop(0)


class FakeDB:
    """记录 SQL 执行次数；可设置固定 EXPLAIN 成本。"""

    def __init__(self, responses, cost=0.0):
        self.responses = list(responses)
        self.cost = cost
        self.queries = []
        self.explains = 0

    async def explain(self, sql_text, tenant_id, timeout_ms=5000):
        self.explains += 1
        return self.cost

    async def execute(
        self, sql_text, tenant_id, max_rows=200, timeout_ms=5000
    ):
        self.queries.append((sql_text, tenant_id))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _result(value=100) -> QueryResult:
    return QueryResult(
        columns=["revenue"],
        rows=[(value,)],
        row_count=1,
        truncated=False,
        duration_ms=1.0,
    )


def _payload(intent=None, question="2026 年 9 月收入") -> dict:
    return {
        "question": question,
        "tenant_id": "tenant_a",
        "intent": intent or {},
        "request_id": "test",
        "user_id": "tester",
    }


def _intent() -> dict:
    return {"intent": "answer", "metrics": ["revenue"]}


def _sql(value=1) -> str:
    return (
        f"SELECT {value} AS revenue FROM orders "
        "WHERE tenant_id='tenant_a'"
    )


async def test_supervisor_topology_and_handoff():
    model = ScriptedModel(
        [
            SQLPlan(sql=_sql(1)),
            Critique(faithful=True, feedback="ok"),
            AnswerOutput(answer="收入为 100。"),
        ]
    )
    db = FakeDB([_result()])
    graph = build_multi_agent_analytics_graph(model, db)

    state = await graph.ainvoke(_payload(_intent()))

    assert "orders" in state["schema_brief"]
    assert state["sql"]
    assert state["result"]["row_count"] == 1
    assert state["critique_ok"] is True
    assert state["answer"] == "收入为 100。"
    assert state["steps"] == 4
    # Reporter 不能再执行 SQL。
    assert len(db.queries) == 1
    assert model.schemas == [SQLPlan, Critique, AnswerOutput]


async def test_critic_failure_loops_back_to_analyst():
    model = ScriptedModel(
        [
            SQLPlan(sql=_sql(1)),
            Critique(faithful=False, feedback="应只统计已完成订单"),
            SQLPlan(sql=_sql(2)),
            Critique(faithful=True, feedback="ok"),
            AnswerOutput(answer="修正后收入为 100。"),
        ]
    )
    db = FakeDB([_result(100), _result(90)])
    graph = build_multi_agent_analytics_graph(model, db)

    state = await graph.ainvoke(_payload(_intent()))

    assert len(db.queries) == 2
    assert state["replan_count"] == 1
    assert state["critic_rejections"] == 1
    assert state["steps"] == MAX_STEPS
    assert state["answer"] == "修正后收入为 100。"


async def test_max_steps_terminates_without_reporter():
    model = ScriptedModel(
        [
            SQLPlan(sql=_sql(1)),
            Critique(faithful=False, feedback="不行"),
            SQLPlan(sql=_sql(2)),
            Critique(faithful=False, feedback="还不行"),
            SQLPlan(sql=_sql(3)),
        ],
        forbidden={AnswerOutput},
    )
    db = FakeDB([_result(1), _result(2), _result(3)])
    graph = build_multi_agent_analytics_graph(model, db)

    state = await graph.ainvoke(_payload(_intent()))

    assert state["steps"] >= MAX_STEPS
    assert state["answer"].startswith("分析失败")
    assert AnswerOutput not in model.schemas


async def test_duplicate_sql_is_detected_and_not_reexecuted():
    model = ScriptedModel(
        [
            SQLPlan(sql=_sql(1)),
            Critique(faithful=False, feedback="不行"),
            SQLPlan(sql=_sql(1)),
            SQLPlan(sql=_sql(1)),
            SQLPlan(sql=_sql(1)),
        ]
    )
    db = FakeDB([_result(1)])
    graph = build_multi_agent_analytics_graph(model, db)

    state = await graph.ainvoke(_payload(_intent()))

    assert len(db.queries) == 1
    assert state["duplicate_queries"] >= 1
    assert state["answer"].startswith("分析失败")


async def test_high_cost_rejects_without_execution():
    model = ScriptedModel([SQLPlan(sql=_sql(1))])
    db = FakeDB([], cost=200000)
    graph = build_multi_agent_analytics_graph(model, db)

    state = await graph.ainvoke(_payload(_intent()))

    assert state["rejected"] is True
    assert "成本过高" in state["answer"]
    assert db.queries == []


async def test_scout_handles_clarify_without_sql():
    model = ScriptedModel(
        [Intent(intent="clarify", clarification="请明确时间范围。")]
    )
    db = FakeDB([])
    graph = build_multi_agent_analytics_graph(model, db)

    state = await graph.ainvoke(_payload())

    assert state["clarification"] == "请明确时间范围。"
    assert db.queries == []
    assert state["steps"] == 1


async def test_scout_handles_refuse_without_sql():
    model = ScriptedModel([Intent(intent="refuse")])
    db = FakeDB([])
    graph = build_multi_agent_analytics_graph(model, db)

    state = await graph.ainvoke(_payload())

    assert "无法回答" in state["answer"]
    assert db.queries == []
    assert state["steps"] == 1
