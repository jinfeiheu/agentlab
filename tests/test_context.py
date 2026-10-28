from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from agentlab.agent.context import (
    compress_tool_content,
    estimate_tokens,
    plan_compaction,
    summarize_messages,
    trim_messages,
)
from tests.fakes import FakeRunnable


def test_estimate_tokens_chinese_and_english():
    assert estimate_tokens("你好") == 2
    assert estimate_tokens("hello world") >= 2
    assert estimate_tokens("") == 0


def test_trim_messages_keeps_system_and_recent():
    msgs = [SystemMessage(content="sys")] + [
        HumanMessage(content="x" * 100) for _ in range(10)
    ]
    out = trim_messages(msgs, max_tokens=100)
    assert out[0].type == "system"
    assert len(out) < len(msgs)
    assert out[-1].content == "x" * 100


def test_trim_messages_keeps_tool_call_pair_together():
    msgs = [
        SystemMessage(content="sys"),
        HumanMessage(content="旧问题" * 100),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "calculator",
                    "args": {"expression": "1+1"},
                    "id": "c1",
                }
            ],
        ),
        ToolMessage(content="2", tool_call_id="c1"),
        AIMessage(content="答案"),
    ]
    out = trim_messages(msgs, max_tokens=60)
    assert out[-1].content == "答案"
    assert any(
        isinstance(m, AIMessage) and m.tool_calls for m in out
    )
    assert any(isinstance(m, ToolMessage) for m in out)


def test_trim_messages_never_leaves_orphan_tool_message():
    msgs = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "calculator",
                    "args": {"expression": "1+1"},
                    "id": "c1",
                }
            ],
        ),
        ToolMessage(content="2", tool_call_id="c1"),
        HumanMessage(content="新问题" * 50),
    ]
    out = trim_messages(msgs, max_tokens=10)
    assert not any(isinstance(m, ToolMessage) for m in out)
    assert out[-1].content == "新问题" * 50


def test_compress_tool_content_truncates():
    text = "x" * 1000
    out = compress_tool_content(text, max_chars=100)
    assert out.startswith("x" * 100)
    assert out.endswith("...(已截断)")
    assert len(out) < 1000


def test_summarize_messages_uses_model():
    model = FakeRunnable(AIMessage(content="用户问好"))
    out = summarize_messages(model, [HumanMessage(content="hi")])
    assert "用户问好" in out


def test_plan_compaction_under_budget_returns_none():
    assert plan_compaction([HumanMessage(content="hi")], 100) is None


def test_plan_compaction_splits_old_groups_and_keeps_newest():
    msgs = [
        HumanMessage(content="旧" * 200),
        AIMessage(content="旧答" * 200),
        HumanMessage(content="最新问题"),
    ]
    plan = plan_compaction(msgs, 50)
    assert plan is not None
    old, recent = plan
    assert [m.content for m in recent] == ["最新问题"]
    assert len(old) == 2


def test_plan_compaction_keeps_tool_call_group_together():
    msgs = [
        HumanMessage(content="旧" * 100),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "calculator",
                    "args": {"expression": "1+1"},
                    "id": "c1",
                }
            ],
        ),
        ToolMessage(content="2", tool_call_id="c1"),
        HumanMessage(content="新" * 5),
    ]
    plan = plan_compaction(msgs, 30)
    assert plan is not None
    old, recent = plan
    old_tool = any(isinstance(m, ToolMessage) for m in old)
    old_call = any(isinstance(m, AIMessage) and m.tool_calls for m in old)
    recent_tool = any(isinstance(m, ToolMessage) for m in recent)
    recent_call = any(isinstance(m, AIMessage) and m.tool_calls for m in recent)
    assert old_tool == old_call
    assert recent_tool == recent_call


def test_plan_compaction_keeps_newest_group_even_over_budget():
    msgs = [HumanMessage(content="旧" * 100), HumanMessage(content="新" * 100)]
    plan = plan_compaction(msgs, 30)
    assert plan is not None
    old, recent = plan
    assert [m.content for m in recent] == ["新" * 100]
    assert [m.content for m in old] == ["旧" * 100]
