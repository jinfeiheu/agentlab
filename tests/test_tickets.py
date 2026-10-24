import os

import pytest

import tickets
from auth import UserContext
from tests.fakes import FakeRuntime

integration = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="需要真实 Postgres 与 seed 数据;设置 RUN_INTEGRATION=1 后运行",
)


def test_can_access_ticket():
    assert tickets.can_access_ticket("user_alice", "user_alice")
    assert not tickets.can_access_ticket("user_bob", "user_alice")


def test_can_access_ticket_rejects_missing_ids():
    assert not tickets.can_access_ticket("", "user_alice")
    assert not tickets.can_access_ticket("user_alice", "")


def test_get_ticket_denies_cross_user(monkeypatch):
    monkeypatch.setattr(
        tickets,
        "fetch_ticket",
        lambda tid: {"user_id": "user_bob", "subject": "x", "status": "open"},
    )
    runtime = FakeRuntime(UserContext(user_id="user_alice"))
    result = tickets.get_ticket.func("T-2001", runtime)
    assert "无权限" in result or "未找到" in result


def test_get_ticket_returns_own_ticket(monkeypatch):
    monkeypatch.setattr(
        tickets,
        "fetch_ticket",
        lambda tid: {
            "ticket_id": tid,
            "user_id": "user_alice",
            "subject": "无法登录",
            "status": "open",
        },
    )
    runtime = FakeRuntime(UserContext(user_id="user_alice"))
    result = tickets.get_ticket.func("T-1001", runtime)
    assert "T-1001" in result
    assert "无法登录" in result
    assert "open" in result


def test_get_ticket_not_found(monkeypatch):
    monkeypatch.setattr(tickets, "fetch_ticket", lambda tid: None)
    runtime = FakeRuntime(UserContext(user_id="user_alice"))
    result = tickets.get_ticket.func("T-9999", runtime)
    assert "未找到或无权限" in result


def test_get_ticket_handles_db_error(monkeypatch):
    def broken(tid):
        raise RuntimeError("db down")

    monkeypatch.setattr(tickets, "fetch_ticket", broken)
    runtime = FakeRuntime(UserContext(user_id="user_alice"))
    result = tickets.get_ticket.func("T-1001", runtime)
    assert "查询失败" in result


@integration
@pytest.mark.integration
def test_fetch_ticket_reads_seeded_row():
    ticket = tickets.fetch_ticket("T-1001")
    assert ticket is not None
    assert ticket["user_id"] == "user_alice"
    assert ticket["subject"] == "无法登录"
