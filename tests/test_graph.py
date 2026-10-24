import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command
from pydantic import Field

import graph as graph_module
from auth import UserContext
from graph import build_graph
from memory import MemoryItem, save_memory, search_memory, upsert_memory
from tests.fakes import FakeEmbeddings
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


class CapturingModel(BaseChatModel):
    """记录 agent 节点实际收到的消息。"""

    responses: list[AIMessage]
    calls: int = 0
    seen: list[list] = Field(default_factory=list)

    @property
    def _llm_type(self):
        return "capturing"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(list(messages))
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


def test_graph_trims_context_before_model_call(monkeypatch):
    monkeypatch.setattr(graph_module, "CONTEXT_MAX_TOKENS", 40)
    monkeypatch.setattr(
        graph_module, "plan_compaction", lambda *args, **kwargs: None
    )
    model = CapturingModel(responses=[AIMessage(content="ok")])
    compiled = build_graph(model, [calculator])
    compiled.invoke(
        {
            "messages": [
                HumanMessage(content="旧问题" * 400),
                AIMessage(content="旧回答" * 400),
                HumanMessage(content="最新问题"),
            ]
        },
        {"configurable": {"thread_id": "t14"}},
    )
    sent = model.seen[0]
    assert sent[-1].content == "最新问题"
    assert len(sent) == 2


def test_graph_compacts_old_messages_into_summary(monkeypatch):
    monkeypatch.setattr(graph_module, "CONTEXT_MAX_TOKENS", 40)
    model = CapturingModel(
        responses=[AIMessage(content="旧对话摘要"), AIMessage(content="回答")]
    )
    compiled = build_graph(model, [calculator])
    result = compiled.invoke(
        {
            "messages": [
                HumanMessage(content="旧问题" * 200),
                AIMessage(content="旧回答" * 200),
                HumanMessage(content="最新问题"),
            ]
        },
        {"configurable": {"thread_id": "t17"}},
    )
    assert result["summary"] == "旧对话摘要"
    assert not any("旧问题" in str(m.content) for m in result["messages"])
    assert not any("旧回答" in str(m.content) for m in result["messages"])
    assert result["messages"][-1].content == "回答"
    assert "旧对话摘要" in model.seen[1][0].content


def test_graph_does_not_compact_under_threshold():
    model = CapturingModel(responses=[AIMessage(content="回答")])
    compiled = build_graph(model, [calculator])
    result = compiled.invoke(
        {"messages": [HumanMessage(content="hi")]},
        {"configurable": {"thread_id": "t18"}},
    )
    assert len(model.seen) == 1
    assert not result.get("summary")


def test_agent_injects_profile_from_store():
    store = InMemoryStore(index={"embed": FakeEmbeddings(dim=4), "dims": 4})
    upsert_memory(
        store,
        "user_alice",
        MemoryItem("profile", "profile.name", "小明"),
    )
    model = CapturingModel(responses=[AIMessage(content="ok")])
    compiled = build_graph(model, [calculator], store=store)
    compiled.invoke(
        {"messages": [HumanMessage(content="hi")]},
        {"configurable": {"thread_id": "t21"}},
        context=UserContext(user_id="user_alice"),
    )
    system_prompt = model.seen[0][0].content
    assert "profile.name" in system_prompt
    assert "小明" in system_prompt


def test_compaction_writes_episode_when_auto_memory_enabled(monkeypatch):
    monkeypatch.setattr(graph_module, "CONTEXT_MAX_TOKENS", 40)
    monkeypatch.setattr(graph_module, "ENABLE_AUTO_MEMORY", True)
    store = InMemoryStore(index={"embed": FakeEmbeddings(dim=4), "dims": 4})
    model = CapturingModel(
        responses=[AIMessage(content="旧对话摘要"), AIMessage(content="回答")]
    )
    compiled = build_graph(model, [calculator], store=store)
    compiled.invoke(
        {
            "messages": [
                HumanMessage(content="旧问题" * 200),
                AIMessage(content="旧回答" * 200),
                HumanMessage(content="最新问题"),
            ]
        },
        {"configurable": {"thread_id": "t22"}},
        context=UserContext(user_id="user_alice"),
    )
    episodes = store.search(
        ("user", "user_alice", "episode"), query="摘要", limit=5
    )
    assert len(episodes) == 1
    assert episodes[0].value["value"] == "旧对话摘要"
    assert episodes[0].key == "episode:t22"


def test_compaction_skips_episode_when_auto_memory_disabled(monkeypatch):
    monkeypatch.setattr(graph_module, "CONTEXT_MAX_TOKENS", 40)
    monkeypatch.setattr(graph_module, "ENABLE_AUTO_MEMORY", False)
    store = InMemoryStore(index={"embed": FakeEmbeddings(dim=4), "dims": 4})
    model = CapturingModel(
        responses=[AIMessage(content="旧对话摘要"), AIMessage(content="回答")]
    )
    compiled = build_graph(model, [calculator], store=store)
    compiled.invoke(
        {
            "messages": [
                HumanMessage(content="旧问题" * 200),
                AIMessage(content="旧回答" * 200),
                HumanMessage(content="最新问题"),
            ]
        },
        {"configurable": {"thread_id": "t23"}},
        context=UserContext(user_id="user_alice"),
    )
    episodes = store.search(
        ("user", "user_alice", "episode"), query="摘要", limit=5
    )
    assert episodes == []


def test_graph_summary_persists_across_turns(monkeypatch):
    monkeypatch.setattr(graph_module, "CONTEXT_MAX_TOKENS", 40)
    model = CapturingModel(
        responses=[
            AIMessage(content="摘要"),
            AIMessage(content="回答1"),
            AIMessage(content="回答2"),
        ]
    )
    compiled = build_graph(model, [calculator], InMemorySaver())
    config = {"configurable": {"thread_id": "t20"}}
    compiled.invoke(
        {
            "messages": [
                HumanMessage(content="旧" * 200),
                AIMessage(content="旧答" * 200),
                HumanMessage(content="第一问"),
            ]
        },
        config,
    )
    compiled.invoke(
        {"messages": [HumanMessage(content="第二问")]}, config
    )
    state = compiled.get_state(config)
    assert state.values["summary"] == "摘要"
    assert state.values["messages"][-1].content == "回答2"
    assert len(model.seen) == 3


def test_graph_compaction_does_not_leave_orphan_tool_message(monkeypatch):
    monkeypatch.setattr(graph_module, "CONTEXT_MAX_TOKENS", 60)
    model = CapturingModel(
        responses=[AIMessage(content="摘要"), AIMessage(content="回答")]
    )
    compiled = build_graph(model, [calculator])
    result = compiled.invoke(
        {
            "messages": [
                HumanMessage(content="旧" * 200),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "calculator",
                            "args": {"expression": "1+1"},
                            "id": "c-old",
                        }
                    ],
                ),
                ToolMessage(content="2", tool_call_id="c-old"),
                HumanMessage(content="新" * 100),
            ]
        },
        {"configurable": {"thread_id": "t19"}},
    )
    messages = result["messages"]
    for index, message in enumerate(messages):
        if isinstance(message, ToolMessage):
            assert any(
                isinstance(previous, AIMessage) and previous.tool_calls
                for previous in messages[:index]
            )


def _memory_responses() -> list[AIMessage]:
    return [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "save_memory",
                    "args": {"key": "name", "value": "小明"},
                    "id": "m1",
                }
            ],
        ),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_memory",
                    "args": {"query": "名字"},
                    "id": "m2",
                }
            ],
        ),
        AIMessage(content="完成"),
    ]


def test_graph_memory_tools_use_context_and_store():
    store = InMemoryStore(index={"embed": FakeEmbeddings(dim=4), "dims": 4})
    compiled = build_graph(
        ScriptedModel(responses=_memory_responses()),
        [save_memory, search_memory],
        store=store,
    )
    result = compiled.invoke(
        {"messages": [("user", "记住我叫小明")]},
        {"configurable": {"thread_id": "t15"}},
        context=UserContext(user_id="user_alice"),
    )
    tool_messages = [m for m in result["messages"] if m.type == "tool"]
    assert "已记住" in tool_messages[0].content
    assert "小明" in tool_messages[1].content


async def test_graph_async_memory_tools_use_context_and_store():
    store = InMemoryStore(index={"embed": FakeEmbeddings(dim=4), "dims": 4})
    compiled = build_graph(
        ScriptedModel(responses=_memory_responses()),
        [save_memory, search_memory],
        store=store,
    )
    result = await compiled.ainvoke(
        {"messages": [("user", "记住我叫小明")]},
        {"configurable": {"thread_id": "t16"}},
        context=UserContext(user_id="user_alice"),
    )
    tool_messages = [m for m in result["messages"] if m.type == "tool"]
    assert "已记住" in tool_messages[0].content
    assert "小明" in tool_messages[1].content
