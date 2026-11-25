"""架构路由测试：single/multi 选择与 auto 入口。"""

from agentlab.analytics.graph import Intent
from agentlab.analytics.routing import AutoAnalyticsGraph, route_question


def test_simple_metric_routes_single():
    intent = {"intent": "answer", "metrics": ["revenue"]}
    assert route_question("2026 年 9 月收入", intent) == "single"


def test_multi_metrics_route_multi():
    intent = {
        "intent": "answer",
        "metrics": ["revenue", "refund_rate"],
    }
    assert route_question("收入与退款率对比", intent) == "multi"


def test_multi_dimensions_route_multi():
    intent = {
        "intent": "answer",
        "metrics": ["gmv"],
        "dimensions": ["channel", "region"],
    }
    assert route_question("各渠道各区域 GMV", intent) == "multi"


def test_comparison_keyword_routes_multi():
    intent = {"intent": "answer", "metrics": ["gmv"]}
    assert route_question("对比各渠道 GMV", intent) == "multi"


def test_clarify_and_refuse_stay_single():
    assert (
        route_question(
            "最近收入怎么样",
            {"intent": "clarify", "ambiguous": True},
        )
        == "single"
    )
    assert (
        route_question("NPS 是多少", {"intent": "refuse"})
        == "single"
    )


class _StubGraph:
    def __init__(self, name: str):
        self.name = name
        self.calls = []

    async def ainvoke(self, payload, config=None):
        self.calls.append(payload)
        return {"answer": self.name}


async def test_auto_injects_intent_and_routes():
    single = _StubGraph("single")
    multi = _StubGraph("multi")

    async def classifier(question, tenant_id, config=None):
        return Intent(
            intent="answer", metrics=["revenue", "refund_rate"]
        )

    auto = AutoAnalyticsGraph(single, multi, classifier)
    state = await auto.ainvoke(
        {
            "question": "收入与退款率对比",
            "tenant_id": "tenant_a",
            "intent": {},
        }
    )

    assert state["route"] == "multi"
    assert len(multi.calls) == 1
    assert multi.calls[0]["intent"]["metrics"] == [
        "revenue",
        "refund_rate",
    ]
    assert single.calls == []


async def test_auto_skips_classifier_when_intent_present():
    single = _StubGraph("single")
    multi = _StubGraph("multi")
    called = []

    async def classifier(question, tenant_id, config=None):
        called.append(question)
        return Intent(intent="answer")

    auto = AutoAnalyticsGraph(single, multi, classifier)
    state = await auto.ainvoke(
        {
            "question": "2026 年 9 月收入",
            "tenant_id": "tenant_a",
            "intent": {"intent": "answer", "metrics": ["revenue"]},
        }
    )

    assert called == []
    assert state["route"] == "single"
    assert len(single.calls) == 1
