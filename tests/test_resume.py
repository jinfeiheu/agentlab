"""HITL resume 测试:/chat/resume 与 SSE interrupt 事件。"""

from types import SimpleNamespace

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from tests.fakes import auth_client, bearer, fake_services

QUESTION = "确认发送这份报告吗?"
CONTENT = "测试报告"


def _interrupt_state(pending: bool = True):
    interrupts = (
        (SimpleNamespace(value={"question": QUESTION, "content": CONTENT}),)
        if pending
        else ()
    )
    return SimpleNamespace(values={"messages": []}, interrupts=interrupts)


class InterruptGraph:
    """第一次有 pending interrupt;resume 后消费掉。"""

    def __init__(self):
        self.inputs = []
        self.configs = []
        self.pending = True

    async def aget_state(self, config):
        return _interrupt_state(self.pending)

    async def ainvoke(self, payload, config=None, **kwargs):
        self.inputs.append(payload)
        self.configs.append(config)
        self.pending = False
        return {"messages": [AIMessage(content="resumed")]}


class NoInterruptGraph:
    """没有 pending interrupt,resume 应直接 409。"""

    async def aget_state(self, config):
        return _interrupt_state(pending=False)

    async def ainvoke(self, payload, config=None, **kwargs):
        raise AssertionError("没有 interrupt 时不应调用 ainvoke")


class StreamingInterruptGraph:
    """流式输出结束后仍有 pending interrupt。"""

    async def astream(self, payload, config=None, stream_mode=None, **kwargs):
        yield ("messages", (AIMessageChunk(content="请确认"), {}))
        yield ("updates", {})

    async def aget_state(self, config):
        return _interrupt_state(pending=True)


class ChatGraph:
    """非流式 /chat:回答后返回 pending interrupt。"""

    async def ainvoke(self, payload, config=None, **kwargs):
        return {"messages": [AIMessage(content="请确认")]}

    async def aget_state(self, config):
        return _interrupt_state(pending=True)


class StreamingResumeGraph:
    """恢复后继续流式输出,并带回工具结果。"""

    def __init__(self):
        self.inputs = []
        self.configs = []
        self.pending = True

    async def aget_state(self, config):
        return _interrupt_state(self.pending)

    async def astream(self, payload, config=None, stream_mode=None, **kwargs):
        self.inputs.append(payload)
        self.configs.append(config)
        self.pending = False
        yield ("messages", (AIMessageChunk(content="已发送"), {}))
        yield (
            "updates",
            {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content="已发送(模拟):测试报告",
                            name="send_report",
                            tool_call_id="call-1",
                        )
                    ]
                }
            },
        )


def test_resume_without_interrupt_returns_409():
    graph = NoInterruptGraph()
    client, token = auth_client(fake_services(graph=graph))
    response = client.post(
        "/chat/resume",
        headers=bearer(token),
        json={"session_id": "s1", "answer": "y"},
    )
    assert response.status_code == 409


def test_resume_yes_uses_command():
    graph = InterruptGraph()
    client, token = auth_client(fake_services(graph=graph))
    response = client.post(
        "/chat/resume",
        headers=bearer(token),
        json={"session_id": "s1", "answer": "y"},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "resumed"
    assert graph.inputs[0].resume == "y"


def test_resume_no_uses_command():
    graph = InterruptGraph()
    client, token = auth_client(fake_services(graph=graph))
    response = client.post(
        "/chat/resume",
        headers=bearer(token),
        json={"session_id": "s1", "answer": "n"},
    )
    assert response.status_code == 200
    assert graph.inputs[0].resume == "n"


def test_resume_is_scoped_to_user():
    graph = InterruptGraph()
    client, token = auth_client(fake_services(graph=graph))
    client.post(
        "/chat/resume",
        headers=bearer(token),
        json={"session_id": "user_bob:s1", "answer": "y"},
    )
    assert graph.configs[0]["configurable"]["thread_id"] == "user_alice:user_bob:s1"


def test_resume_second_time_returns_409():
    graph = InterruptGraph()
    client, token = auth_client(fake_services(graph=graph))
    payload = {"session_id": "s1", "answer": "y"}
    first = client.post("/chat/resume", headers=bearer(token), json=payload)
    second = client.post("/chat/resume", headers=bearer(token), json=payload)
    assert first.status_code == 200
    assert second.status_code == 409
    assert len(graph.inputs) == 1


def test_resume_requires_auth():
    graph = InterruptGraph()
    client, _token = auth_client(fake_services(graph=graph))
    response = client.post(
        "/chat/resume", json={"session_id": "s1", "answer": "y"}
    )
    assert response.status_code == 401


def test_stream_emits_interrupt_event():
    graph = StreamingInterruptGraph()
    client, token = auth_client(fake_services(graph=graph))
    with client.stream(
        "POST",
        "/chat/stream",
        headers=bearer(token),
        json={"message": "发送报告", "session_id": "s1"},
    ) as response:
        body = "".join(response.iter_text())
    assert '"type": "interrupt"' in body
    assert QUESTION in body
    assert CONTENT in body


def test_stream_resume_without_interrupt_returns_409():
    graph = NoInterruptGraph()
    client, token = auth_client(fake_services(graph=graph))
    response = client.post(
        "/chat/stream/resume",
        headers=bearer(token),
        json={"session_id": "s1", "answer": "y"},
    )
    assert response.status_code == 409


def test_stream_resume_emits_token_tool_result_and_done():
    graph = StreamingResumeGraph()
    client, token = auth_client(fake_services(graph=graph))
    with client.stream(
        "POST",
        "/chat/stream/resume",
        headers=bearer(token),
        json={"session_id": "s1", "answer": "y"},
    ) as response:
        body = "".join(response.iter_text())
    assert response.status_code == 200
    assert '"type": "token"' in body
    assert "已发送" in body
    assert '"type": "tool_result"' in body
    assert '"tool_call_id": "call-1"' in body
    assert '"type": "done"' in body
    assert graph.inputs[0].resume == "y"
    assert graph.configs[0]["configurable"]["thread_id"] == "user_alice:s1"


def test_stream_resume_requires_auth():
    graph = StreamingResumeGraph()
    client, _token = auth_client(fake_services(graph=graph))
    response = client.post(
        "/chat/stream/resume",
        json={"session_id": "s1", "answer": "y"},
    )
    assert response.status_code == 401


def test_stream_resume_second_time_returns_409():
    graph = StreamingResumeGraph()
    client, token = auth_client(fake_services(graph=graph))
    payload = {"session_id": "s1", "answer": "y"}
    first = client.post(
        "/chat/stream/resume", headers=bearer(token), json=payload
    )
    second = client.post(
        "/chat/stream/resume", headers=bearer(token), json=payload
    )
    assert first.status_code == 200
    assert second.status_code == 409


def test_chat_response_includes_interrupt():
    graph = ChatGraph()
    client, token = auth_client(fake_services(graph=graph))
    response = client.post(
        "/chat",
        headers=bearer(token),
        json={"message": "发送报告", "session_id": "s1"},
    )
    assert response.status_code == 200
    assert response.json()["interrupt"]["question"] == QUESTION
    assert response.json()["interrupt"]["content"] == CONTENT
