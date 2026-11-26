"""Analytics API：非流式、SSE 计划事件、越权与取消。"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from agentlab.api.analytics.services import AnalyticsServices
from agentlab.api.app import create_app
from agentlab.analytics.session import AnalyticsSessionStore
from agentlab.security.auth import sign_token
from tests.fakes import fake_services


@pytest.fixture(autouse=True)
def _stub_audit(monkeypatch):
    async def noop(**kwargs):
        return None

    monkeypatch.setattr(
        "agentlab.analytics.graph.write_audit", noop, raising=False
    )
    monkeypatch.setattr(
        "agentlab.api.analytics.events.write_audit", noop, raising=False
    )


class FakeAnalyticsGraph:
    def __init__(self, state=None, updates=None):
        self.state = state or {}
        self.updates = updates or []

    async def ainvoke(self, payload, config=None):
        return {**payload, **self.state}

    async def astream(self, payload, config=None, stream_mode=None):
        for update in self.updates:
            yield update


def _client(graph, sessions=None):
    analytics = AnalyticsServices(
        graph=graph,
        sessions=sessions or AnalyticsSessionStore(),
    )
    app = create_app(services=fake_services(), analytics=analytics)
    return TestClient(app), analytics, app


def _auth(user_id="user_alice"):
    return {"Authorization": f"Bearer {sign_token(user_id)}"}


def test_analytics_chat_returns_table_and_audit_id():
    graph = FakeAnalyticsGraph(
        state={
            "answer": "收入为 100。",
            "sql": "SELECT 100 AS revenue",
            "result": {
                "columns": ["revenue"],
                "rows": [[100]],
                "row_count": 1,
            },
            "chart_spec": {"mark": "bar"},
        }
    )
    client, analytics, _ = _client(graph)

    response = client.post(
        "/analytics/chat",
        headers=_auth(),
        json={"message": "2026 年 9 月收入", "session_id": "s1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "收入为 100。"
    assert body["sql"].startswith("SELECT")
    assert body["columns"] == ["revenue"]
    assert body["rows"] == [[100]]
    assert body["chart_spec"] == {"mark": "bar"}
    assert body["audit_id"]
    assert "2026 年 9 月收入" in analytics.sessions.context(
        "user_alice", "s1"
    )


def test_analytics_chat_rejects_cross_tenant_request():
    client, _, _ = _client(FakeAnalyticsGraph())

    response = client.post(
        "/analytics/chat",
        headers=_auth("user_alice"),
        json={
            "message": "查询 tenant_b 收入",
            "session_id": "s1",
            "tenant_id": "tenant_b",
        },
    )

    assert response.status_code == 403


def test_analytics_chat_returns_clarification():
    graph = FakeAnalyticsGraph(
        state={
            "answer": "",
            "clarification": "请明确时间范围。",
            "result": {},
        }
    )
    client, _, _ = _client(graph)

    response = client.post(
        "/analytics/chat",
        headers=_auth(),
        json={"message": "最近收入怎么样", "session_id": "s1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["clarification"] == "请明确时间范围。"
    assert body["status"] == "clarify"


def test_analytics_chat_redacts_pii():
    graph = FakeAnalyticsGraph(
        state={
            "answer": "联系 alice@example.com",
            "result": {"columns": ["x"], "rows": [["13800138000"]]},
        }
    )
    client, _, _ = _client(graph)

    response = client.post(
        "/analytics/chat",
        headers=_auth(),
        json={"message": "联系信息", "session_id": "s1"},
    )

    body = response.json()
    assert "alice@example.com" not in body["answer"]
    assert "[EMAIL]" in body["answer"]
    assert "13800138000" not in str(body["rows"])


def test_analytics_stream_emits_plan_events():
    graph = FakeAnalyticsGraph(
        updates=[
            {"understand": {"intent": {"intent": "answer"}}},
            {"plan_sql": {"sql": "SELECT 1 AS x"}},
            {"validate_sql": {"sql": "SELECT 1 AS x", "sql_error": ""}},
            {
                "execute": {
                    "result": {
                        "columns": ["x"],
                        "rows": [[1]],
                        "row_count": 1,
                    }
                }
            },
            {
                "answer": {
                    "answer": "结果为 1。",
                    "chart_spec": {"mark": "bar"},
                }
            },
        ]
    )
    client, analytics, _ = _client(graph)

    with client.stream(
        "POST",
        "/analytics/chat/stream",
        headers=_auth(),
        json={"message": "查询 1", "session_id": "s1"},
    ) as response:
        body = "".join(response.iter_text())

    for event_type in (
        "plan_created",
        "step_started",
        "step_result",
        "verification",
        "final",
    ):
        assert f'"type": "{event_type}"' in body
    assert '"audit_id"' in body
    assert "查询 1" in analytics.sessions.context("user_alice", "s1")


def test_analytics_cancel_cancels_registered_task():
    client, _, app = _client(FakeAnalyticsGraph())

    class _Task:
        def __init__(self):
            self.cancelled = False

        def done(self):
            return False

        def cancel(self):
            self.cancelled = True

    task = _Task()
    app.state.analytics_tasks["user_alice:s1"] = {
        "task": task,
        "request_id": "req-1",
    }

    response = client.post(
        "/analytics/cancel",
        headers=_auth(),
        json={"session_id": "s1"},
    )

    assert response.status_code == 200
    assert response.json()["cancelled"] is True
    assert task.cancelled is True


class RecordingAnalyticsGraph(FakeAnalyticsGraph):
    def __init__(self):
        super().__init__(
            state={
                "answer": "结果",
                "sql": "SELECT 1",
                "intent": {
                    "metrics": ["revenue"],
                    "dimensions": ["channel"],
                    "time_range": "2026-09",
                },
                "result": {
                    "columns": ["x"],
                    "rows": [[1]],
                    "row_count": 1,
                },
            }
        )
        self.payloads = []

    async def ainvoke(self, payload, config=None):
        self.payloads.append(dict(payload))
        return await super().ainvoke(payload, config)


def test_analytics_chat_reuses_session_context_and_isolates_users():
    graph = RecordingAnalyticsGraph()
    client, _, _ = _client(graph)

    first = client.post(
        "/analytics/chat",
        headers=_auth("user_alice"),
        json={"message": "2026 年 9 月各渠道收入", "session_id": "s1"},
    )
    assert first.status_code == 200
    second = client.post(
        "/analytics/chat",
        headers=_auth("user_alice"),
        json={"message": "按地区拆一下", "session_id": "s1"},
    )
    assert second.status_code == 200
    assert "2026 年 9 月各渠道收入" in graph.payloads[1][
        "conversation_context"
    ]

    bob = client.post(
        "/analytics/chat",
        headers=_auth("user_bob"),
        json={"message": "按地区拆一下", "session_id": "s1"},
    )
    assert bob.status_code == 200
    assert graph.payloads[2]["conversation_context"] == ""


def test_analytics_page_served():
    client, _, _ = _client(FakeAnalyticsGraph())
    response = client.get("/analytics")
    assert response.status_code == 200
    assert "数据分析 Agent" in response.text


def test_analytics_cancel_unknown_task():
    client, _, _ = _client(FakeAnalyticsGraph())

    response = client.post(
        "/analytics/cancel",
        headers=_auth(),
        json={"session_id": "missing"},
    )

    assert response.status_code == 200
    assert response.json()["cancelled"] is False
