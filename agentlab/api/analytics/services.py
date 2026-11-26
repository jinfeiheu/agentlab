"""Analytics API 的服务集合。"""

from dataclasses import dataclass

from agentlab.analytics.db import AnalyticsDB
from agentlab.analytics.graph import build_analytics_graph
from agentlab.analytics.session import AnalyticsSessionStore
from agentlab.analytics.versioning import build_model_router
from agentlab.models import build_chat_model


@dataclass
class AnalyticsServices:
    """Analytics 图与会话表；测试可注入 fake。"""

    graph: object
    sessions: AnalyticsSessionStore
    db_check: object = None

    async def aclose(self) -> None:
        return None


def build_analytics_services() -> AnalyticsServices:
    """生产依赖：单 Agent 图 + 进程内会话。"""
    model = build_chat_model(temperature=0)
    graph = build_analytics_graph(
        model,
        AnalyticsDB(),
        model_router=build_model_router(temperature=0),
    )
    return AnalyticsServices(
        graph=graph,
        sessions=AnalyticsSessionStore(),
    )
