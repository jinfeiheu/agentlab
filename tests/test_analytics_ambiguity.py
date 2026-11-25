"""歧义澄清与不可回答拒答的行为测试。"""

import pytest

from agentlab.analytics import graph as graph_module
from agentlab.analytics.graph import (
    Intent,
    build_analytics_graph,
    run_analytics_question,
)

AMBIGUOUS_QUESTIONS = [
    "最近收入怎么样？",
    "上个月退款情况如何？",
    "按地区拆一下",
    "哪个品类卖得最好？",
]

UNANSWERABLE_QUESTIONS = [
    "tenant_a 的 NPS 是多少？",
    "tenant_a 的库存周转率是多少？",
    "tenant_a 的毛利率是多少？",
    "tenant_a 的客户满意度是多少？",
]


class _IntentModel:
    """固定返回 clarify/refuse，模拟 understand 节点的判断。"""

    def __init__(self, intent: Intent):
        self.intent = intent

    def with_structured_output(self, schema, **kwargs):
        return self

    async def ainvoke(self, prompt, **kwargs):
        return self.intent


class _NoExecuteDB:
    """歧义/拒答路径不应执行 SQL；一旦执行就失败。"""

    async def explain(self, *args, **kwargs):
        return 0.0

    async def execute(self, *args, **kwargs):
        raise AssertionError("歧义/拒答问题不应执行 SQL")


@pytest.fixture(autouse=True)
def _stub_audit(monkeypatch):
    """离线测试不写真实审计表。"""

    async def noop(**kwargs):
        return None

    monkeypatch.setattr(
        graph_module, "write_audit", noop, raising=False
    )


@pytest.mark.parametrize("question", AMBIGUOUS_QUESTIONS)
async def test_ambiguous_questions_clarify(question):
    model = _IntentModel(
        Intent(
            intent="clarify",
            ambiguous=True,
            clarification="请明确时间范围、指标口径和维度。",
        )
    )
    graph = build_analytics_graph(model, _NoExecuteDB())

    result = await run_analytics_question(graph, question, "tenant_a")

    assert result["clarification"]
    assert result["sql"] == ""
    assert result["result"] == {}
    assert result["request_id"]


@pytest.mark.parametrize("question", UNANSWERABLE_QUESTIONS)
async def test_unanswerable_questions_refuse(question):
    model = _IntentModel(Intent(intent="refuse"))
    graph = build_analytics_graph(model, _NoExecuteDB())

    result = await run_analytics_question(graph, question, "tenant_a")

    assert "无法" in result["answer"]
    assert result["sql"] == ""
    assert result["result"] == {}
    assert result["request_id"]
