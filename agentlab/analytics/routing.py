"""架构路由：简单题走单 Agent，复杂题走多 Agent；歧义/拒答留在单 Agent。"""

from typing import Literal

from agentlab.analytics.graph import Intent, classify_question

_MULTI_KEYWORDS = (
    "对比",
    "比较",
    "分别",
    "同时",
    "交叉",
    "关联",
    "环比",
    "同比",
    "然后",
    "再按",
    "并且按",
)


def route_question(
    question: str, intent: dict
) -> Literal["single", "multi"]:
    """按意图与问题结构选架构；clarify/refuse 不进入 multi。"""
    intent_name = (intent or {}).get("intent")
    if intent_name in {"clarify", "refuse"}:
        return "single"
    if (intent or {}).get("ambiguous"):
        return "single"
    metrics = [
        metric
        for metric in ((intent or {}).get("metrics") or [])
        if metric
    ]
    dimensions = [
        dimension
        for dimension in ((intent or {}).get("dimensions") or [])
        if dimension
    ]
    if len(metrics) >= 2 or len(dimensions) >= 2:
        return "multi"
    text = question or ""
    if any(keyword in text for keyword in _MULTI_KEYWORDS):
        return "multi"
    if text.count("？") + text.count("?") > 1:
        return "multi"
    return "single"


class AutoAnalyticsGraph:
    """auto 架构：先做一次意图分类，再选择 single/multi。"""

    def __init__(self, single_graph, multi_graph, classifier):
        self.single_graph = single_graph
        self.multi_graph = multi_graph
        self.classifier = classifier

    async def ainvoke(self, payload: dict, config=None):
        intent = payload.get("intent") or {}
        if not intent:
            result = await self.classifier(
                payload["question"], payload["tenant_id"], config
            )
            if isinstance(result, Intent):
                intent = result.model_dump()
            elif hasattr(result, "model_dump"):
                intent = result.model_dump()
            else:
                intent = dict(result)
        route = route_question(payload["question"], intent)
        graph = (
            self.multi_graph if route == "multi" else self.single_graph
        )
        state = await graph.ainvoke(
            {**payload, "intent": intent}, config or {}
        )
        state = dict(state)
        state["route"] = route
        state["intent"] = intent
        return state


def build_auto_analytics_graph(model, single_graph, multi_graph):
    """生产用 auto 图：复用单 Agent 的意图解析器。"""

    async def classifier(question: str, tenant_id: str, config=None):
        return await classify_question(
            model, question, tenant_id, config=config
        )

    return AutoAnalyticsGraph(single_graph, multi_graph, classifier)
