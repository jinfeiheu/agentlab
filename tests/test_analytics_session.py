"""多轮分析会话：上下文复用、压缩与隔离。"""

from agentlab.analytics.session import (
    AnalyticsSession,
    AnalyticsSessionStore,
)


def _state(metrics=None, dimensions=None, time_range="", sql="SELECT 1"):
    return {
        "intent": {
            "metrics": metrics or ["revenue"],
            "dimensions": dimensions or ["channel"],
            "time_range": time_range or "2026-09",
        },
        "sql": sql,
        "answer": "结果",
    }


def test_session_context_reuses_previous_turn():
    session = AnalyticsSession()
    session.record("2026 年 9 月各渠道收入", _state())

    context = session.context()

    assert "各渠道收入" in context
    assert "指标：revenue" in context
    assert "维度：channel" in context
    assert "时间：2026-09" in context


def test_session_context_compresses_old_turns():
    session = AnalyticsSession(max_chars=160)
    session.record("第一轮问题" * 10, _state())
    session.record("第二轮问题", _state(metrics=["gmv"]))

    context = session.context()

    assert len(context) <= 160
    assert "第二轮问题" in context
    assert "第一轮问题" * 10 not in context


def test_session_context_truncates_single_oversized_turn():
    session = AnalyticsSession(max_chars=80)
    session.record("超长问题" * 50, _state())

    context = session.context()

    assert len(context) <= 80


def test_session_store_isolates_users_and_sessions():
    store = AnalyticsSessionStore()
    store.record("user_alice", "s1", "收入", _state())
    store.record("user_bob", "s1", "退款", _state(metrics=["refund_rate"]))

    alice = store.context("user_alice", "s1")
    bob = store.context("user_bob", "s1")
    other = store.context("user_alice", "s2")

    assert "收入" in alice
    assert "退款" not in alice
    assert "退款" in bob
    assert other == ""
    assert store.count() == 3


def test_session_reset():
    store = AnalyticsSessionStore()
    store.record("user_alice", "s1", "收入", _state())
    store.reset("user_alice", "s1")

    assert store.context("user_alice", "s1") == ""
