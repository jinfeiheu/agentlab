import asyncio
import json
from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    ToolMessage,
)

import api
from api import create_app
from auth import sign_token
from tests.fakes import RecordingGraph, auth_client, bearer, fake_services


def test_login_required():
    client = TestClient(create_app(services=fake_services()))
    response = client.post(
        "/chat", json={"message": "hi", "session_id": "s1"}
    )
    assert response.status_code == 401


def test_login_endpoint():
    client = TestClient(create_app(services=fake_services()))
    ok = client.post(
        "/login", json={"username": "alice", "password": "alice-pass"}
    )
    assert ok.status_code == 200
    assert ok.json()["token"]
    bad = client.post(
        "/login", json={"username": "alice", "password": "wrong"}
    )
    assert bad.status_code == 401


def test_chat_non_streaming():
    client, token = auth_client(fake_services())
    response = client.post(
        "/chat",
        headers=bearer(token),
        json={"message": "hi", "session_id": "s1"},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "fake answer"


def test_chat_stream_emits_token_and_done():
    client, token = auth_client(fake_services())
    with client.stream(
        "POST",
        "/chat/stream",
        headers=bearer(token),
        json={"message": "hi", "session_id": "s1"},
    ) as response:
        body = "".join(response.iter_text())
    assert '"type": "token"' in body
    assert '"type": "done"' in body


def test_thread_id_is_scoped_to_user():
    fake = RecordingGraph()
    client, token_a = auth_client(fake_services(graph=fake))
    client.post(
        "/chat",
        headers=bearer(token_a),
        json={"message": "hi", "session_id": "same"},
    )
    assert fake.configs[0]["configurable"]["thread_id"] == "user_alice:same"


def test_invalid_token_rejected():
    client = TestClient(create_app(services=fake_services()))
    response = client.post(
        "/chat",
        headers={"Authorization": "Bearer not-a-token"},
        json={"message": "hi", "session_id": "s1"},
    )
    assert response.status_code == 401


def test_rate_limit_returns_429(monkeypatch):
    monkeypatch.setattr(api, "RATE_LIMIT_PER_MINUTE", 1)
    client, token = auth_client(fake_services())
    payload = {"message": "hi", "session_id": "s1"}
    assert (
        client.post("/chat", headers=bearer(token), json=payload).status_code
        == 200
    )
    assert (
        client.post("/chat", headers=bearer(token), json=payload).status_code
        == 429
    )


def test_healthz():
    client = TestClient(create_app(services=fake_services()))
    assert client.get("/healthz").json() == {"status": "ok"}


def test_healthz_runs_db_check_when_configured():
    calls = []
    services = fake_services()
    services.db_check = lambda: calls.append("check")
    client = TestClient(create_app(services=services))
    assert client.get("/healthz").json() == {"status": "ok"}
    assert calls == ["check"]


def test_healthz_returns_503_when_db_check_fails():
    async def failing_check():
        raise RuntimeError("connection refused")

    services = fake_services()
    services.db_check = failing_check
    client = TestClient(create_app(services=services))
    response = client.get("/healthz")
    assert response.status_code == 503
    assert "数据库不可用" in response.json()["detail"]


def test_lifespan_sets_up_and_shuts_down_tracing(monkeypatch):
    calls = []
    monkeypatch.setattr(
        api, "setup_tracing", lambda: calls.append("setup"), raising=False
    )
    monkeypatch.setattr(
        api, "shutdown_tracing", lambda: calls.append("shutdown"), raising=False
    )
    async def fake_build_services():
        return fake_services()

    monkeypatch.setattr(api, "build_services", fake_build_services)

    with TestClient(create_app()) as client:
        assert calls == ["setup"]
        assert client.get("/healthz").status_code == 200

    assert calls == ["setup", "shutdown"]


def test_lifespan_degrades_when_services_fail(monkeypatch):
    async def failing_build_services():
        raise RuntimeError("connection refused")

    monkeypatch.setattr(api, "setup_tracing", lambda: None)
    monkeypatch.setattr(api, "shutdown_tracing", lambda: None)
    monkeypatch.setattr(api, "build_services", failing_build_services)

    with TestClient(create_app()) as client:
        response = client.get("/healthz")

    assert response.status_code == 503
    assert "服务初始化失败" in response.json()["detail"]


def test_index_serves_page():
    client = TestClient(create_app(services=fake_services()))
    response = client.get("/")
    assert response.status_code == 200
    assert "登录" in response.text


class FailingGraph:
    async def ainvoke(self, *args, **kwargs):
        raise RuntimeError("boom")

    async def astream(self, *args, **kwargs):
        raise RuntimeError("boom")
        yield  # pragma: no cover


def test_chat_stream_graph_error_emits_error():
    client, token = auth_client(fake_services(graph=FailingGraph()))
    with client.stream(
        "POST",
        "/chat/stream",
        headers=bearer(token),
        json={"message": "hi", "session_id": "s1"},
    ) as response:
        body = "".join(response.iter_text())
    assert '"type": "error"' in body
    assert "boom" in body


class ToolStreamGraph:
    async def astream(self, payload, config=None, stream_mode=None, **kwargs):
        call = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_docs",
                    "args": {"query": "x"},
                    "id": "call-1",
                }
            ],
        )
        long_result = (
            "[来源:a.md#A]\n" + ("片段" * 300) + "\n[来源:b.md#B]"
        )
        yield ("updates", {"agent": {"messages": [call]}})
        yield (
            "updates",
            {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content=long_result,
                            name="search_docs",
                            tool_call_id="call-1",
                        )
                    ]
                }
            },
        )
        yield ("messages", (AIMessageChunk(content="答案"), {}))
        yield ("updates", {})


def _stream_events(body: str) -> list[dict]:
    return [
        json.loads(line[len("data: ") :])
        for line in body.splitlines()
        if line.startswith("data: ")
    ]


def test_chat_stream_collects_all_tool_sources():
    client, token = auth_client(fake_services(graph=ToolStreamGraph()))
    with client.stream(
        "POST",
        "/chat/stream",
        headers=bearer(token),
        json={"message": "hi", "session_id": "s1"},
    ) as response:
        body = "".join(response.iter_text())
    events = _stream_events(body)
    done = next(event for event in events if event["type"] == "done")
    assert "a.md#A" in done["sources"]
    assert "b.md#B" in done["sources"]


def test_chat_stream_tool_events_include_call_ids():
    client, token = auth_client(fake_services(graph=ToolStreamGraph()))
    with client.stream(
        "POST",
        "/chat/stream",
        headers=bearer(token),
        json={"message": "hi", "session_id": "s1"},
    ) as response:
        body = "".join(response.iter_text())
    events = _stream_events(body)
    call = next(event for event in events if event["type"] == "tool_call")
    result = next(event for event in events if event["type"] == "tool_result")
    assert call["id"] == "call-1"
    assert result["tool_call_id"] == "call-1"


class ToolInMessagesGraph:
    async def astream(self, payload, config=None, stream_mode=None, **kwargs):
        yield (
            "messages",
            (
                ToolMessage(
                    content="RAW TOOL OUTPUT",
                    name="search_docs",
                    tool_call_id="call-1",
                ),
                {},
            ),
        )
        yield ("messages", (AIMessageChunk(content="final answer"), {}))
        yield ("updates", {})


def test_chat_stream_does_not_emit_tool_messages_as_tokens():
    client, token = auth_client(fake_services(graph=ToolInMessagesGraph()))
    with client.stream(
        "POST",
        "/chat/stream",
        headers=bearer(token),
        json={"message": "hi", "session_id": "s1"},
    ) as response:
        body = "".join(response.iter_text())
    events = _stream_events(body)
    text = "".join(
        event["text"] for event in events if event["type"] == "token"
    )
    assert "RAW TOOL OUTPUT" not in text
    assert "final answer" in text


def test_pending_tool_calls_detects_dangling_and_intervening():
    call = AIMessage(
        content="",
        tool_calls=[{"name": "search_docs", "args": {"query": "x"}, "id": "c1"}],
    )
    assert api._pending_tool_calls([call]) == ({"c1": "search_docs"}, True)
    resolved = ToolMessage(content="ok", name="search_docs", tool_call_id="c1")
    assert api._pending_tool_calls([call, resolved]) == ({}, True)
    assert api._pending_tool_calls([call, HumanMessage(content="next")]) == (
        {"c1": "search_docs"},
        False,
    )


class DanglingGraph:
    def __init__(self):
        self.updates = []
        self.state = SimpleNamespace(
            values={
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "search_docs",
                                "args": {"query": "x"},
                                "id": "c1",
                            }
                        ],
                    )
                ]
            },
            interrupts=(),
        )

    async def aget_state(self, config):
        return self.state

    async def aupdate_state(self, config, values, as_node=None):
        self.updates.append((values, as_node))

    async def ainvoke(self, payload, config=None, **kwargs):
        return {"messages": [AIMessage(content="recovered")]}


def test_chat_repairs_dangling_tool_call():
    graph = DanglingGraph()
    client, token = auth_client(fake_services(graph=graph))
    response = client.post(
        "/chat",
        headers=bearer(token),
        json={"message": "next", "session_id": "s1"},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "recovered"
    assert len(graph.updates) == 1
    values, as_node = graph.updates[0]
    assert as_node == "tools"
    repaired = values["messages"][0]
    assert isinstance(repaired, ToolMessage)
    assert repaired.tool_call_id == "c1"


class FakeCheckpointer:
    def __init__(self):
        self.deleted = []

    async def adelete_thread(self, thread_id):
        self.deleted.append(thread_id)


class InterruptedGraph:
    def __init__(self):
        self.checkpointer = FakeCheckpointer()

    async def aget_state(self, config):
        return SimpleNamespace(
            values={"messages": []},
            interrupts=(SimpleNamespace(value="confirm?"),),
        )

    async def ainvoke(self, payload, config=None, **kwargs):
        return {"messages": [AIMessage(content="after reset")]}


def test_chat_resets_interrupted_thread():
    graph = InterruptedGraph()
    client, token = auth_client(fake_services(graph=graph))
    response = client.post(
        "/chat",
        headers=bearer(token),
        json={"message": "next", "session_id": "s1"},
    )
    assert response.status_code == 200
    assert graph.checkpointer.deleted == ["user_alice:s1"]


class SerialGraph:
    def __init__(self):
        self.active = 0
        self.max_active = 0

    async def ainvoke(self, payload, config=None, **kwargs):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.05)
        self.active -= 1
        return {"messages": [AIMessage(content="ok")]}


async def test_chat_serializes_same_thread():
    graph = SerialGraph()
    app = create_app(services=fake_services(graph=graph))
    token = sign_token("user_alice")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        responses = await asyncio.gather(
            client.post(
                "/chat",
                headers=bearer(token),
                json={"message": "a", "session_id": "same"},
            ),
            client.post(
                "/chat",
                headers=bearer(token),
                json={"message": "b", "session_id": "same"},
            ),
        )
    assert [response.status_code for response in responses] == [200, 200]
    assert graph.max_active == 1


class SlowGraph:
    async def ainvoke(self, *args, **kwargs):
        await asyncio.sleep(1)
        return {"messages": []}


def test_chat_timeout(monkeypatch):
    monkeypatch.setattr(api, "REQUEST_TIMEOUT", 0.01)
    client, token = auth_client(fake_services(graph=SlowGraph()))
    response = client.post(
        "/chat",
        headers=bearer(token),
        json={"message": "hi", "session_id": "s1"},
    )
    assert response.status_code == 504
