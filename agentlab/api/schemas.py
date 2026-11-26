"""API 请求与响应模型。"""

from pydantic import BaseModel


class AnalyticsChatRequest(BaseModel):
    """一轮数据分析请求；tenant_id 仅用于越权校验。"""

    message: str
    session_id: str
    tenant_id: str | None = None


class AnalyticsChatResponse(BaseModel):
    """数据分析响应；rows/chart_spec 供页面直接渲染。"""

    answer: str
    sql: str = ""
    columns: list[str] = []
    rows: list = []
    chart_spec: dict | None = None
    audit_id: str = ""
    clarification: str = ""
    status: str = "success"


class AnalyticsCancelRequest(BaseModel):
    """取消某个会话正在执行的分析任务。"""

    session_id: str


class AnalyticsCancelResponse(BaseModel):
    """取消结果；unknown 表示没有运行中的任务。"""

    cancelled: bool
    status: str = "ok"
