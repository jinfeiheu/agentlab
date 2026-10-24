import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from graph import build_graph
from tools import calculator, send_report


@tool
def unlisted_tool() -> str:
    """故意不在安全白名单里的工具。"""
    return "should not be registered"


def test_graph_rejects_tool_outside_allowlist():
    model = ScriptedModel(responses=[AIMessage(content="ok")])
    with pytest.raises(RuntimeError, match="白名单"):
        build_graph(model, [calculator, unlisted_tool])


class ScriptedModel(BaseChatModel):
    responses: list[AIMessage]
    calls: int = 0

    @property
    def _llm_type(self):
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        message = self.responses[self.calls % len(self.responses)]
        self.calls += 1
        return ChatResult(generations=[ChatGeneration(message=message)])


def test_graph_runs_tool_loop():
    model = ScriptedModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "calculator", "args": {"expression": "2+3*4"}, "id": "c1"}
                ],
            ),
            AIMessage(content="答案是 14"),
        ]
    )
    graph = build_graph(model, [calculator])
    result = graph.invoke(
        {"messages": [("user", "算一下")]}, {"configurable": {"thread_id": "t1"}}
    )
    assert result["messages"][-1].content == "答案是 14"
    assert any(m.type == "tool" and m.content == "14" for m in result["messages"])


def test_send_report_interrupt_and_resume():
    model = ScriptedModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "send_report", "args": {"content": "周报"}, "id": "c2"}
                ],
            ),
            AIMessage(content="处理完成"),
        ]
    )
    graph = build_graph(model, [send_report], checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "t2"}}
    graph.invoke({"messages": [("user", "发送周报")]}, config)
    assert graph.get_state(config).interrupts
    result = graph.invoke(Command(resume="y"), config)
    assert result["messages"][-1].content == "处理完成"
    assert any(m.type == "tool" and "已发送" in m.content for m in result["messages"])


def test_send_report_cancel():
    model = ScriptedModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "send_report", "args": {"content": "周报"}, "id": "c3"}
                ],
            ),
            AIMessage(content="已取消"),
        ]
    )
    graph = build_graph(model, [send_report], checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "t3"}}
    graph.invoke({"messages": [("user", "发送周报")]}, config)
    result = graph.invoke(Command(resume="n"), config)
    assert any(m.type == "tool" and "已取消" in m.content for m in result["messages"])


def test_graph_denies_unknown_tool():
    model = ScriptedModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "delete_everything",
                        "args": {},
                        "id": "c9",
                    }
                ],
            ),
            AIMessage(content="已拒绝"),
        ]
    )
    graph = build_graph(model, [calculator])
    result = graph.invoke(
        {"messages": [("user", "删除全部数据")]},
        {"configurable": {"thread_id": "t9"}},
    )
    tool_messages = [m for m in result["messages"] if m.type == "tool"]
    assert tool_messages
    assert "拒绝" in tool_messages[0].content
    assert result["messages"][-1].content == "已拒绝"
