"""SQL 守卫的离线测试：只允许单条只读 SELECT。"""

import pytest

from agentlab.analytics.sql_guard import validate_sql

ALLOWED = {
    "customers",
    "customers_safe",
    "products",
    "orders",
    "order_items",
    "refunds",
    "subscriptions",
    "usage_events",
    "tickets",
    "metric_catalog",
}


def test_guard_rejects_multi_statement():
    result = validate_sql("SELECT 1; DROP TABLE orders", ALLOWED)
    assert result.allowed is False
    assert result.reason


def test_guard_rejects_comment_hidden_statement():
    sql = "SELECT 1 /* ok */; -- bypass\nDROP TABLE orders"
    assert validate_sql(sql, ALLOWED).allowed is False


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM orders",
        "UPDATE orders SET status='x'",
        "CREATE TABLE x(id int)",
        "DROP TABLE orders",
        "ALTER TABLE orders ADD COLUMN x int",
        "COPY orders TO '/tmp/orders.csv'",
        "SET search_path TO public",
    ],
)
def test_guard_rejects_dml_ddl_and_admin(sql):
    assert validate_sql(sql, ALLOWED).allowed is False


def test_guard_rejects_system_tables():
    assert validate_sql("SELECT * FROM pg_catalog.pg_tables", ALLOWED).allowed is False
    assert (
        validate_sql("SELECT * FROM information_schema.tables", ALLOWED).allowed
        is False
    )


def test_guard_rejects_system_tables_in_subquery():
    sql = "SELECT * FROM (SELECT * FROM pg_catalog.pg_tables) t"
    assert validate_sql(sql, ALLOWED).allowed is False


def test_guard_rejects_unknown_relation():
    assert validate_sql("SELECT * FROM secret_table", ALLOWED).allowed is False


def test_guard_rejects_dml_in_cte():
    sql = "WITH d AS (DELETE FROM orders RETURNING *) SELECT * FROM d"
    assert validate_sql(sql, ALLOWED).allowed is False


def test_guard_adds_limit():
    result = validate_sql("SELECT * FROM orders", ALLOWED)
    assert result.allowed is True
    assert "LIMIT" in result.normalized_sql.upper()


def test_guard_clamps_large_limit():
    result = validate_sql("SELECT * FROM orders LIMIT 5000", ALLOWED)
    assert result.allowed is True
    assert "LIMIT 1000" in result.normalized_sql.upper()
