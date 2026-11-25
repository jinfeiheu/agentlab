"""Analytics 安全测试：跨租户隔离与 PII 防护。"""

import os
import uuid

import pytest

from agentlab.analytics.catalog import ALLOWED_RELATIONS
from agentlab.analytics.db import AnalyticsDB, AnalyticsDBError
from agentlab.analytics.sql_guard import validate_sql

TEST_ANALYTICS_DB = os.getenv("TEST_ANALYTICS_DATABASE_URL") or os.getenv(
    "ANALYTICS_DATABASE_URL",
    "postgresql://analytics_reader:analytics_reader@localhost:5432/agentlab",
)
AUDIT_DSN = (
    os.getenv("TEST_ANALYTICS_AUDIT_DATABASE_URL")
    or os.getenv("ANALYTICS_AUDIT_DATABASE_URL")
    or os.getenv("ANALYTICS_SEED_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or "postgresql://postgres:postgres@localhost:5432/agentlab"
)


def _fetch_audit(request_id: str):
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(AUDIT_DSN) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM analytics.analytics_audit "
                "WHERE request_id = %s",
                (request_id,),
            )
            return cur.fetchone()


async def _write_audit(**kwargs):
    from agentlab.analytics.audit import write_audit

    await write_audit(**kwargs)

requires_db = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="需要真实 Postgres 与 RLS；设置 RUN_INTEGRATION=1 后运行",
)


@pytest.fixture
def analytics_db():
    """只读连接；租户上下文由 execute 的 SET LOCAL 注入。"""
    return AnalyticsDB(TEST_ANALYTICS_DB)


@pytest.mark.integration
@requires_db
async def test_tenant_a_cannot_read_tenant_b(analytics_db):
    try:
        result = await analytics_db.execute(
            "SELECT * FROM orders WHERE tenant_id = 'tenant_b'",
            tenant_id="tenant_a",
            max_rows=10,
        )
    except AnalyticsDBError:
        # 数据库直接拒绝也算通过，但更希望 RLS 返回空集。
        return
    assert result.row_count == 0


@pytest.mark.integration
@requires_db
async def test_orders_only_return_current_tenant(analytics_db):
    result = await analytics_db.execute(
        "SELECT tenant_id FROM orders",
        tenant_id="tenant_a",
        max_rows=200,
    )
    assert result.rows
    assert {row[0] for row in result.rows} == {"tenant_a"}


@pytest.mark.integration
@requires_db
async def test_customers_safe_only_return_current_tenant(analytics_db):
    result = await analytics_db.execute(
        "SELECT tenant_id FROM customers_safe",
        tenant_id="tenant_a",
        max_rows=200,
    )
    assert result.rows
    assert {row[0] for row in result.rows} == {"tenant_a"}


@pytest.mark.integration
@requires_db
async def test_order_items_isolated_via_orders(analytics_db):
    result = await analytics_db.execute(
        "SELECT o.tenant_id FROM order_items oi "
        "JOIN orders o ON o.order_id = oi.order_id",
        tenant_id="tenant_a",
        max_rows=200,
    )
    assert result.rows
    assert {row[0] for row in result.rows} == {"tenant_a"}


@pytest.mark.integration
@requires_db
async def test_customers_safe_has_no_pii_columns(analytics_db):
    result = await analytics_db.execute(
        "SELECT * FROM customers_safe LIMIT 1",
        tenant_id="tenant_a",
    )
    columns = {column.lower() for column in result.columns}
    assert not ({"name", "email", "phone"} & columns)


@pytest.mark.integration
@requires_db
@pytest.mark.parametrize("pii", ["alice@example.com", "13800138000"])
async def test_db_error_redacts_pii(analytics_db, pii):
    with pytest.raises(AnalyticsDBError) as exc_info:
        await analytics_db.execute(
            f"SELECT * FROM orders WHERE order_date = '{pii}'",
            tenant_id="tenant_a",
        )
    assert pii not in str(exc_info.value)


def test_raw_customers_rejected_by_guard():
    assert (
        validate_sql("SELECT * FROM customers", ALLOWED_RELATIONS).allowed
        is False
    )
    assert (
        validate_sql(
            "SELECT email FROM customers", ALLOWED_RELATIONS
        ).allowed
        is False
    )


@pytest.mark.integration
@requires_db
async def test_write_audit_records_success():
    request_id = f"req-{uuid.uuid4().hex}"
    await _write_audit(
        request_id=request_id,
        user_id="user_alice",
        tenant_id="tenant_a",
        question="2026 年 9 月收入",
        sql="SELECT 1",
        status="success",
        row_count=3,
        estimated_cost=1.23,
        duration_ms=45.6,
    )
    row = _fetch_audit(request_id)
    assert row is not None
    assert row["request_id"] == request_id
    assert row["user_id"] == "user_alice"
    assert row["tenant_id"] == "tenant_a"
    assert row["status"] == "success"
    assert row["row_count"] == 3
    assert float(row["estimated_cost"]) == 1.23
    assert row["duration_ms"] == 46
    assert row["created_at"] is not None
    assert row["approved_by"] is None


@pytest.mark.integration
@requires_db
@pytest.mark.parametrize("status", ["error", "rejected", "clarify", "refuse"])
async def test_write_audit_records_outcomes(status):
    request_id = f"req-{uuid.uuid4().hex}"
    await _write_audit(
        request_id=request_id,
        user_id="user_alice",
        tenant_id="tenant_a",
        question="测试问题",
        sql="",
        status=status,
        row_count=0,
        estimated_cost=0.0,
        duration_ms=1.0,
    )
    row = _fetch_audit(request_id)
    assert row is not None
    assert row["status"] == status


@pytest.mark.integration
@requires_db
async def test_write_audit_redacts_pii():
    request_id = f"req-{uuid.uuid4().hex}"
    await _write_audit(
        request_id=request_id,
        user_id="user_alice",
        tenant_id="tenant_a",
        question="联系 alice@example.com 或 13800138000 查询收入",
        sql="SELECT * FROM orders WHERE note = 'alice@example.com'",
        status="success",
        row_count=1,
        estimated_cost=0.0,
        duration_ms=1.0,
    )
    row = _fetch_audit(request_id)
    assert row is not None
    assert "alice@example.com" not in row["question"]
    assert "13800138000" not in row["question"]
    assert "alice@example.com" not in row["sql"]
