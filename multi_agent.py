"""手写 Supervisor 多 Agent:researcher -> writer -> critic 回环。"""

import json
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command
from pydantic import BaseModel

from auth import UserContext
from rag import format_docs

MAX_STEPS = 6


class MultiAgentState(TypedDict, total=False):
    """多 Agent 共享状态:消息 + 研究/草稿/评审 + 路由步数。"""

    messages: Annotated[list[AnyMessage], add_messages]
    research_notes: str
    draft: str
    review: str
    steps: int
    next: str


class Route(BaseModel):
    """Supervisor 的合法路由集合。"""

    next: Literal["researcher", "writer", "critic", "__end__"]


class Critique(BaseModel):
    """Critic 的结构化评审结果。"""

    faithful: bool
    feedback: str = ""


WRITER_PROMPT = """你是写作 Agent。只依据研究笔记回答用户问题,不要编造。
如果笔记不足以回答,直接说明无法回答。
引用格式:[来源:文件名#章节]

用户问题:{question}
研究笔记:{notes}
"""

CRITIC_PROMPT = """你是严格的评审 Agent。判断草稿是否只依据研究笔记、是否回答了问题。
只输出 JSON,不要输出其他文字:
{{"faithful": true 或 false, "feedback": "一句话说明问题或 ok"}}

用户问题:{question}
研究笔记:{notes}
草稿:{draft}
"""


def decide_next(state) -> str:
    """纯路由函数:按步数、研究、草稿、评审决定下一个节点。"""
    steps = int(state.get("steps", 0) or 0)
    if steps >= MAX_STEPS:
        return "__end__"
    if not state.get("research_notes"):
        return "researcher"
    if not state.get("draft"):
        return "writer"
    if not state.get("review"):
        return "critic"
    if state.get("review") == "ok":
        return "__end__"
    return "writer"


def _message_text(message) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    return str(content)


def _last_question(state) -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage) or getattr(
            message, "type", None
        ) == "human":
            return _message_text(message)
    return ""


def _steps(state) -> int:
    return int(state.get("steps", 0) or 0)


def _coerce_critique(result) -> Critique:
    if isinstance(result, Critique):
        return result
    if isinstance(result, dict):
        return Critique.model_validate(result)
    content = getattr(result, "content", result)
    if isinstance(content, str):
        text = content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end >= start:
            return Critique.model_validate(
                json.loads(text[start : end + 1])
            )
    raise ValueError("无法解析评审结果")


def build_multi_agent_graph(
    model, retriever, checkpointer=None, store=None
):
    """构建手写 supervisor 图;writer 重置 review 以便重新进入 critic。"""
    critic_chain = model.with_structured_output(
        Critique, method="json_mode"
    )

    def researcher(state):
        question = _last_question(state)
        try:
            docs = retriever.invoke(question)
            notes = (
                format_docs(list(docs))
                if docs
                else "知识库中没有找到相关内容。"
            )
        except Exception as exc:  # noqa: BLE001 - 检索失败也让图继续
            notes = f"检索失败:{exc}"
        return {"research_notes": notes, "steps": _steps(state) + 1}

    def writer(state):
        question = _last_question(state)
        notes = state.get("research_notes", "")
        result = model.invoke(
            WRITER_PROMPT.format(question=question, notes=notes)
        )
        draft = _message_text(result)
        # 新草稿需要重新评审,否则 supervisor 会一直路由回 writer。
        return {
            "messages": [AIMessage(content=draft)],
            "draft": draft,
            "review": "",
            "steps": _steps(state) + 1,
        }

    def critic(state):
        question = _last_question(state)
        notes = state.get("research_notes", "")
        draft = state.get("draft", "")
        prompt = CRITIC_PROMPT.format(
            question=question, notes=notes, draft=draft
        )
        try:
            verdict = _coerce_critique(critic_chain.invoke(prompt))
        except Exception as exc:  # noqa: BLE001 - 评审失败默认通过,避免死循环
            verdict = Critique(
                faithful=True, feedback=f"评审失败,默认通过:{exc}"
            )
        review = "ok" if verdict.faithful else (
            verdict.feedback or "需要修改"
        )
        return {"review": review, "steps": _steps(state) + 1}

    def supervisor(state):
        route = Route(next=decide_next(state)).next
        return Command(goto=route, update={"next": route})

    builder = StateGraph(MultiAgentState, context_schema=UserContext)
    builder.add_node("researcher", researcher)
    builder.add_node("writer", writer)
    builder.add_node("critic", critic)
    builder.add_node("supervisor", supervisor)
    builder.add_edge(START, "supervisor")
    # 每个 worker 完成后回到 supervisor 重新路由。
    builder.add_edge("researcher", "supervisor")
    builder.add_edge("writer", "supervisor")
    builder.add_edge("critic", "supervisor")
    return builder.compile(checkpointer=checkpointer, store=store)
