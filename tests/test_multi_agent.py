from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

import models
from multi_agent import build_multi_agent_graph, decide_next
from tests.fakes import FakeRetriever


def test_supervisor_routes_to_researcher_first():
    state = {"research_notes": "", "draft": "", "review": "", "steps": 0}
    assert decide_next(state) == "researcher"


def test_supervisor_routes_to_writer_after_research():
    state = {"research_notes": "notes", "draft": "", "review": "", "steps": 1}
    assert decide_next(state) == "writer"


def test_supervisor_finishes_after_review():
    state = {"research_notes": "n", "draft": "d", "review": "ok", "steps": 3}
    assert decide_next(state) == "__end__"


def test_supervisor_stops_at_max_steps():
    state = {"research_notes": "n", "draft": "d", "review": "", "steps": 6}
    assert decide_next(state) == "__end__"


def test_supervisor_retries_writer_on_bad_review():
    state = {
        "research_notes": "n",
        "draft": "d",
        "review": "需要补充来源",
        "steps": 3,
    }
    assert decide_next(state) == "writer"


class MultiAgentModel:
    """写作调用返回草稿,评审调用返回预设 verdict。"""

    def __init__(self, verdicts):
        self.verdicts = list(verdicts)
        self.prompts = []

    def with_structured_output(self, schema, **kwargs):
        return self

    def invoke(self, prompt, **kwargs):
        self.prompts.append(prompt)
        if "faithful" in prompt:
            faithful = self.verdicts.pop(0) if self.verdicts else True
            return {
                "faithful": faithful,
                "feedback": "ok" if faithful else "需要补充来源",
            }
        return AIMessage(content="草稿内容 [来源:a.md#A]")


def make_retriever() -> FakeRetriever:
    return FakeRetriever(
        [
            Document(
                page_content="checkpointer 保存图状态。",
                metadata={"source": "a.md", "section": "A"},
            )
        ]
    )


def make_graph(verdicts):
    model = MultiAgentModel(verdicts)
    graph = build_multi_agent_graph(model, make_retriever())
    return graph, model


def test_multi_agent_runs_researcher_writer_critic():
    graph, model = make_graph([True])
    result = graph.invoke({"messages": [("user", "checkpointer 是什么")]})
    assert result["research_notes"]
    assert "草稿内容" in result["draft"]
    assert result["review"] == "ok"
    assert result["steps"] == 3
    assert result["messages"][-1].content == result["draft"]
    critic_prompts = [prompt for prompt in model.prompts if "faithful" in prompt]
    assert len(critic_prompts) == 1


def test_multi_agent_rewrites_after_bad_review():
    graph, model = make_graph([False, True])
    result = graph.invoke({"messages": [("user", "checkpointer 是什么")]})
    assert result["review"] == "ok"
    assert result["steps"] == 5
    critic_prompts = [prompt for prompt in model.prompts if "faithful" in prompt]
    assert len(critic_prompts) == 2


def test_multi_agent_second_turn_resets_scratchpad():
    model = MultiAgentModel([True, True])
    graph = build_multi_agent_graph(
        model, make_retriever(), InMemorySaver()
    )
    config = {"configurable": {"thread_id": "multi-two-turns"}}
    reset = {"research_notes": "", "draft": "", "review": "", "steps": 0}
    graph.invoke(
        {"messages": [("user", "第一问")], **reset}, config
    )
    result = graph.invoke(
        {"messages": [("user", "第二问")], **reset}, config
    )
    assert result["steps"] == 3
    assert result["review"] == "ok"
    assert result["messages"][-1].content == result["draft"]


def test_multi_agent_stops_at_max_steps():
    graph, _model = make_graph([False] * 10)
    result = graph.invoke({"messages": [("user", "checkpointer 是什么")]})
    assert result["steps"] == 6
    assert result["review"] != "ok"


def test_build_fallback_model_uses_qwen():
    model = models.build_fallback_model()
    assert model.model == "qwen3:8b"
    assert model.temperature == 0
    assert model.reasoning is False


def test_build_invoke_with_fallback_uses_fallback(monkeypatch):
    from langchain_core.runnables import RunnableLambda

    def fail(_):
        raise RuntimeError("primary down")

    primary = RunnableLambda(fail)
    fallback = RunnableLambda(lambda _: AIMessage(content="fallback"))
    monkeypatch.setattr(models, "build_chat_model", lambda **_: primary)
    monkeypatch.setattr(models, "build_fallback_model", lambda: fallback)
    runnable = models.build_invoke_with_fallback()
    assert runnable.invoke("x").content == "fallback"
