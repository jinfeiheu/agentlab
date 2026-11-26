"""RAG Agent 请求与响应模型。"""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """一轮对话请求。"""

    message: str
    session_id: str


class ResumeRequest(BaseModel):
    """恢复一次被 interrupt 暂停的工具调用。"""

    session_id: str
    answer: str


class ChatResponse(BaseModel):
    """非流式对话响应;interrupt 非空表示等待人工确认。"""

    answer: str
    sources: list[str]
    interrupt: dict | None = None
