"""Prompt/模型版本、回滚与请求级成本预算测试。"""

import pytest

from agentlab.analytics import graph as graph_module
from agentlab.analytics.db import QueryResult
from agentlab.analytics.graph import (
    AnswerOutput,
    Intent,
    SQLPlan,
    build_analytics_graph,
    run_analytics_question,
)
from agentlab.analytics.versioning import (
    BudgetExceeded,
    CostBudget,
    ModelRouter,
    PromptNotFound,
    PromptRegistry,
)


def test_registry_loads_versions_and_rolls_back():
    registry = PromptRegistry()
    assert registry.active_version("understand") == "v1"
    assert "v2" in registry.versions("understand")

    rolled_back = PromptRegistry(overrides={"understand": "v2"})
    assert rolled_back.active_version("understand") == "v2"
    text = rolled_back.render(
        "understand",
        schema_brief="schema",
        metric_brief="metrics",
        question="问题",
        tenant_id="tenant_a",
        json_intent="{}",
    )
    assert "v2 路由规则" in text
    assert "问题" in text


def test_registry_rejects_unknown_prompt_and_version():
    registry = PromptRegistry()
    with pytest.raises(PromptNotFound):
        registry.get("missing")
    with pytest.raises(PromptNotFound):
        registry.get("understand", "v99")


def test_cost_budget_charges_and_blocks():
    budget = CostBudget(max_cost=0.004, cost_per_call=0.002)

    assert budget.charge(0.0) == 0.002
    assert budget.charge(0.002) == 0.004
    with pytest.raises(BudgetExceeded, match="成本预算"):
        budget.charge(0.004)


def test_model_router_caches_by_model_id():
    calls = []

    def factory(model_id):
        calls.append(model_id)
        return model_id.upper()

    router = ModelRouter(factory)
    assert router("a") == "A"
    assert router("a") == "A"
    assert router("b") == "B"
    assert calls == ["a", "b"]


class _FixedModel:
    """不管 schema 都返回固定结果；用于验证模型路由。"""

    def __init__(self, result):
        self.result = result
        self.prompts = []

    def with_structured_output(self, schema, **kwargs):
        return self

    async def ainvoke(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return self.result


class _DB:
    async def explain(self, sql_text, tenant_id, timeout_ms=5000):
        return 0.0

    async def execute(
        self, sql_text, tenant_id, max_rows=200, timeout_ms=5000
    ):
        return QueryResult(
            columns=["x"],
            rows=[[1]],
            row_count=1,
            truncated=False,
            duration_ms=1.0,
        )


class _Router:
    def __init__(self, models):
        self.models = models
        self.calls = []

    def __call__(self, model_id):
        self.calls.append(model_id)
        return self.models[model_id]


def _write_prompt_dir(tmp_path):
    (tmp_path / "understand.yaml").write_text(
        """
id: understand
active: v1
versions:
  v1: {model: understand-model, template: "U $question"}
""",
        encoding="utf-8",
    )
    (tmp_path / "plan_sql.yaml").write_text(
        """
id: plan_sql
active: v1
versions:
  v1: {model: sql-model, template: "S $question"}
""",
        encoding="utf-8",
    )
    (tmp_path / "repair.yaml").write_text(
        """
id: repair
active: v1
versions:
  v1: {model: sql-model, template: "R $question"}
""",
        encoding="utf-8",
    )
    (tmp_path / "answer.yaml").write_text(
        """
id: answer
active: v1
versions:
  v1: {model: reporter-model, template: "A $question"}
""",
        encoding="utf-8",
    )
    return PromptRegistry(config_dir=tmp_path)


async def test_graph_routes_models_and_records_versions(
    tmp_path, monkeypatch
):
    audit_calls = []

    async def fake_audit(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(
        graph_module, "write_audit", fake_audit, raising=False
    )
    understand_model = _FixedModel(Intent(intent="answer"))
    sql_model = _FixedModel(
        SQLPlan(sql="SELECT 1 AS x FROM orders WHERE tenant_id='tenant_a'")
    )
    reporter_model = _FixedModel(AnswerOutput(answer="完成"))
    router = _Router(
        {
            "understand-model": understand_model,
            "sql-model": sql_model,
            "reporter-model": reporter_model,
        }
    )
    registry = _write_prompt_dir(tmp_path)
    graph = build_analytics_graph(
        reporter_model,  # 默认模型；router 存在时应被覆盖
        _DB(),
        prompt_registry=registry,
        model_router=router,
    )

    state = await run_analytics_question(
        graph, "问题", "tenant_a", user_id="alice"
    )

    assert state["prompt_versions"] == {
        "understand": "v1",
        "plan_sql": "v1",
        "answer": "v1",
    }
    assert state["model_ids"] == {
        "understand": "understand-model",
        "plan_sql": "sql-model",
        "answer": "reporter-model",
    }
    assert router.calls == [
        "understand-model",
        "sql-model",
        "reporter-model",
    ]
    assert state["answer"] == "完成"
    assert audit_calls[0]["prompt_version"] == (
        "answer=v1,plan_sql=v1,understand=v1"
    )
    assert "understand=understand-model" in audit_calls[0]["model_id"]


async def test_budget_exceeded_returns_readable_answer(
    tmp_path, monkeypatch
):
    audit_calls = []

    async def fake_audit(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(
        graph_module, "write_audit", fake_audit, raising=False
    )
    registry = _write_prompt_dir(tmp_path)
    understand_model = _FixedModel(Intent(intent="answer"))
    sql_model = _FixedModel(
        SQLPlan(sql="SELECT 1 AS x FROM orders WHERE tenant_id='tenant_a'")
    )
    graph = build_analytics_graph(
        understand_model,
        _DB(),
        prompt_registry=registry,
        model_router=_Router(
            {"understand-model": understand_model, "sql-model": sql_model}
        ),
        budget=CostBudget(max_cost=0.001, cost_per_call=0.001),
    )

    state = await run_analytics_question(graph, "问题", "tenant_a")

    assert state["budget_exceeded"] is True
    assert "成本预算" in state["answer"]
    assert audit_calls[0]["status"] == "budget"
