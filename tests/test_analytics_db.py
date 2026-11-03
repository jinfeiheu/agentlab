"""Analytics DB 集成测试：默认跳过，设置 RUN_INTEGRATION=1 才运行。"""

import os

import pytest

TEST_ANALYTICS_DB = os.getenv("TEST_ANALYTICS_DATABASE_URL") or os.getenv(
    "ANALYTICS_DATABASE_URL",
    "postgresql://analytics_reader:analytics_reader@localhost:5432/agentlab",
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION") != "1",
        reason="需要真实 Postgres；设置 RUN_INTEGRATION=1 后运行",
    ),
]


@pytest.fixture
def analytics_db():
    """延迟导入，保证离线测试在实现完成前也能正常跳过。"""
    from agentlab.analytics.db import AnalyticsDB

    return AnalyticsDB(TEST_ANALYTICS_DB)


async def test_reader_role_cannot_write(analytics_db):
    with pytest.raises(Exception):
        await analytics_db.execute("DELETE FROM orders", tenant_id="tenant_a")


async def test_execute_applies_timeout_and_limit(analytics_db):
    result = await analytics_db.execute(
        "SELECT * FROM orders",
        tenant_id="tenant_a",
        max_rows=10,
        timeout_ms=1000,
    )
    assert result.row_count <= 10
