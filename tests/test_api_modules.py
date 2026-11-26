"""API 内部模块拆分后的导入与职责测试。"""


def test_schemas_and_services_are_split():
    from agentlab.api.auth_schemas import LoginRequest, LoginResponse
    from agentlab.api.rag_agent.schemas import (
        ChatRequest,
        ChatResponse,
        ResumeRequest,
    )
    from agentlab.api.rag_agent.services import Services, build_services

    assert ChatRequest(message="hi", session_id="s").session_id == "s"
    assert LoginRequest(username="alice", password="p").username == "alice"
    assert LoginResponse(token="t").token == "t"
    assert ResumeRequest(session_id="s", answer="y").answer == "y"
    assert ChatResponse(answer="a", sources=[]).interrupt is None
    assert callable(build_services)
    assert Services(graph=object()).retriever is None


def test_streaming_and_thread_helpers_are_split():
    from agentlab.api.rag_agent.services import (
        _maybe_extract_memory,
        _pending_tool_calls,
        _post_turn_memory,
        _prepare_thread,
    )
    from agentlab.api.rag_agent.sse import _chat_events, _tool_events
    from agentlab.api.redaction import redact_value
    from agentlab.api.streaming import sse

    assert sse({"type": "done"}) == 'data: {"type": "done"}\n\n'
    assert redact_value({"email": "a@b.com"}) == {"email": "[EMAIL]"}
    assert callable(_chat_events)
    assert callable(_tool_events)
    assert callable(_pending_tool_calls)
    assert callable(_prepare_thread)
    assert callable(_maybe_extract_memory)
    assert callable(_post_turn_memory)
