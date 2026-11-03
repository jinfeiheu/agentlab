"""Analytics seed 集成测试：默认跳过，设置 RUN_INTEGRATION=1 才运行。"""

import os

import psycopg
import pytest

TEST_SEED_DB = (
    os.getenv("TEST_ANALYTICS_SEED_DATABASE_URL")
    or os.getenv("ANALYTICS_SEED_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or "postgresql://postgres:postgres@localhost:5432/agentlab"
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION") != "1",
        reason="需要真实 Postgres；设置 RUN_INTEGRATION=1 后运行",
    ),
]


def _fetch_one(sql: str):
    with psycopg.connect(TEST_SEED_DB) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()[0]


def _fetch_all(sql: str) -> list[tuple]:
    with psycopg.connect(TEST_SEED_DB) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()


@pytest.fixture(scope="module")
def seeded_db():
    """小规模重建数据，避免测试等待完整 seed。"""
    from agentlab.analytics.seed import seed_analytics

    seed_analytics(reset=True, scale=0.01)
    return TEST_SEED_DB


def test_seed_creates_tables_and_rows(seeded_db):
    for table in (
        "customers",
        "products",
        "orders",
        "order_items",
        "refunds",
        "subscriptions",
        "usage_events",
        "tickets",
    ):
        assert _fetch_one(f"SELECT count(*) FROM analytics.{table}") > 0


def test_seed_has_at_least_three_tenants(seeded_db):
    assert (
        _fetch_one("SELECT count(DISTINCT tenant_id) FROM analytics.customers")
        >= 3
    )


def test_metric_catalog_has_core_metrics(seeded_db):
    names = {
        row[0]
        for row in _fetch_all(
            "SELECT name FROM analytics.metric_catalog "
            "WHERE tenant_id = 'tenant_a'"
        )
    }
    assert {"revenue", "refund_rate", "active_customers"} <= names


def test_seed_is_idempotent(seeded_db):
    from agentlab.analytics.seed import seed_analytics

    before = _fetch_one("SELECT count(*) FROM analytics.orders")
    seed_analytics(reset=False, scale=0.01)
    after = _fetch_one("SELECT count(*) FROM analytics.orders")
    assert after == before
