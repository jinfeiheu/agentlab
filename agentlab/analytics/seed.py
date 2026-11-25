"""生成 analytics schema 的合成数据，固定 seed 保证可复现。"""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable, Iterator, Sequence

import psycopg
from faker import Faker

from agentlab.analytics.catalog import METRICS
from agentlab.config import ANALYTICS_SEED_DATABASE_URL

TENANTS = ("tenant_a", "tenant_b", "tenant_c")
TENANT_WEIGHTS = (0.6, 0.3, 0.1)
REFERENCE_DATE = datetime(2026, 10, 1, tzinfo=timezone.utc)

REGIONS = ("华东", "华北", "华南", "西南")
SEGMENTS = ("enterprise", "mid_market", "smb")
CATEGORIES = ("电子产品", "家居", "服饰", "运动", "美妆", "图书")
CHANNELS = ("web", "mobile", "partner")
ORDER_STATUSES = ("completed", "shipped", "pending", "cancelled", "refunded")
ORDER_STATUS_WEIGHTS = (0.70, 0.10, 0.08, 0.07, 0.05)
REFUND_REASONS = ("质量问题", "发错货", "物流延迟", "七天无理由")
PLANS = ("starter", "pro", "enterprise")
PLAN_PRICES = {
    "starter": Decimal("99.00"),
    "pro": Decimal("499.00"),
    "enterprise": Decimal("1999.00"),
}
FEATURES = ("api_calls", "storage", "seats", "reports")
SUBSCRIPTION_STATUSES = ("active", "cancelled", "expired")
SUBSCRIPTION_WEIGHTS = (0.70, 0.15, 0.15)
TICKET_CATEGORIES = ("账单", "技术", "账户", "物流")
TICKET_STATUSES = ("open", "pending", "resolved", "closed")
TICKET_PRIORITIES = ("low", "medium", "high", "urgent")

BASE_COUNTS = {
    "customers": 10_000,
    "products": 500,
    "orders": 100_000,
    "refunds": 8_000,
    "subscriptions": 5_000,
    "usage_events": 500_000,
    "tickets": 20_000,
}

_DDL = (
    "CREATE SCHEMA IF NOT EXISTS analytics",
    """
    CREATE TABLE IF NOT EXISTS analytics.customers (
        customer_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        name TEXT,
        email TEXT,
        phone TEXT,
        region TEXT,
        segment TEXT,
        created_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics.products (
        product_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        unit_price NUMERIC(12, 2) NOT NULL,
        active BOOLEAN NOT NULL DEFAULT TRUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics.orders (
        order_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        order_date TIMESTAMPTZ NOT NULL,
        status TEXT NOT NULL,
        channel TEXT,
        region TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics.order_items (
        order_id TEXT NOT NULL,
        product_id TEXT NOT NULL,
        quantity INT NOT NULL,
        unit_price NUMERIC(12, 2) NOT NULL,
        discount NUMERIC(5, 2) NOT NULL DEFAULT 0,
        PRIMARY KEY (order_id, product_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics.refunds (
        refund_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        order_id TEXT NOT NULL,
        refund_date TIMESTAMPTZ NOT NULL,
        amount NUMERIC(12, 2) NOT NULL,
        reason TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics.subscriptions (
        subscription_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        plan TEXT NOT NULL,
        mrr NUMERIC(12, 2) NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE,
        status TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics.usage_events (
        event_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        event_date DATE NOT NULL,
        feature TEXT NOT NULL,
        count INT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics.tickets (
        ticket_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        category TEXT NOT NULL,
        status TEXT NOT NULL,
        priority TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics.metric_catalog (
        metric_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        name TEXT NOT NULL,
        definition TEXT NOT NULL,
        sql_expression TEXT NOT NULL,
        version TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics.analytics_audit (
        request_id TEXT PRIMARY KEY,
        user_id TEXT,
        tenant_id TEXT,
        question TEXT,
        sql TEXT,
        status TEXT,
        row_count INT,
        estimated_cost NUMERIC(12, 2),
        duration_ms INT,
        approved_by TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE OR REPLACE VIEW analytics.customers_safe
    WITH (security_invoker = true) AS
    SELECT customer_id, tenant_id, region, segment, created_at
    FROM analytics.customers
    """,
    "CREATE INDEX IF NOT EXISTS idx_orders_tenant_date "
    "ON analytics.orders (tenant_id, order_date)",
    "CREATE INDEX IF NOT EXISTS idx_refunds_tenant_date "
    "ON analytics.refunds (tenant_id, refund_date)",
    "CREATE INDEX IF NOT EXISTS idx_subscriptions_tenant "
    "ON analytics.subscriptions (tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_usage_tenant_date "
    "ON analytics.usage_events (tenant_id, event_date)",
    "CREATE INDEX IF NOT EXISTS idx_tickets_tenant_created "
    "ON analytics.tickets (tenant_id, created_at)",
)

_TRUNCATE = """
TRUNCATE analytics.customers, analytics.products, analytics.orders,
         analytics.order_items, analytics.refunds, analytics.subscriptions,
         analytics.usage_events, analytics.tickets, analytics.metric_catalog,
         analytics.analytics_audit
RESTART IDENTITY CASCADE
"""

_RLS_TABLES = (
    "customers",
    "products",
    "orders",
    "refunds",
    "subscriptions",
    "usage_events",
    "tickets",
    "metric_catalog",
    "analytics_audit",
)

CUSTOMER_SQL = """
INSERT INTO analytics.customers
    (customer_id, tenant_id, name, email, phone, region, segment, created_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (customer_id) DO NOTHING
"""

PRODUCT_SQL = """
INSERT INTO analytics.products
    (product_id, tenant_id, name, category, unit_price, active)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (product_id) DO NOTHING
"""

ORDER_SQL = """
INSERT INTO analytics.orders
    (order_id, tenant_id, customer_id, order_date, status, channel, region)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (order_id) DO NOTHING
"""

ORDER_ITEM_SQL = """
INSERT INTO analytics.order_items
    (order_id, product_id, quantity, unit_price, discount)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (order_id, product_id) DO NOTHING
"""

REFUND_SQL = """
INSERT INTO analytics.refunds
    (refund_id, tenant_id, order_id, refund_date, amount, reason)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (refund_id) DO NOTHING
"""

SUBSCRIPTION_SQL = """
INSERT INTO analytics.subscriptions
    (subscription_id, tenant_id, customer_id, plan, mrr,
     start_date, end_date, status)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (subscription_id) DO NOTHING
"""

USAGE_SQL = """
INSERT INTO analytics.usage_events
    (event_id, tenant_id, customer_id, event_date, feature, count)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (event_id) DO NOTHING
"""

TICKET_SQL = """
INSERT INTO analytics.tickets
    (ticket_id, tenant_id, customer_id, created_at, category, status, priority)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (ticket_id) DO NOTHING
"""

METRIC_SQL = """
INSERT INTO analytics.metric_catalog
    (metric_id, tenant_id, name, definition, sql_expression, version)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (metric_id) DO UPDATE SET
    name = EXCLUDED.name,
    definition = EXCLUDED.definition,
    sql_expression = EXCLUDED.sql_expression,
    version = EXCLUDED.version
"""


@dataclass(frozen=True)
class Customer:
    customer_id: str
    tenant_id: str
    name: str
    email: str | None
    phone: str | None
    region: str
    segment: str
    created_at: datetime


@dataclass(frozen=True)
class Product:
    product_id: str
    tenant_id: str
    name: str
    category: str
    unit_price: Decimal
    active: bool


@dataclass(frozen=True)
class Order:
    order_id: str
    tenant_id: str
    customer_id: str
    order_date: datetime
    status: str
    channel: str | None
    region: str | None


def _count(base: int, scale: float) -> int:
    return max(1, int(base * scale))


def _pick_tenant(rng: random.Random) -> str:
    return rng.choices(TENANTS, weights=TENANT_WEIGHTS, k=1)[0]


def _random_datetime(rng: random.Random, max_days: int) -> datetime:
    return REFERENCE_DATE - timedelta(
        days=rng.randint(0, max_days),
        seconds=rng.randint(0, 86_399),
    )


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _prepare_schema(conn) -> None:
    with conn.cursor() as cur:
        for statement in _DDL:
            cur.execute(statement)


def _ensure_rls(conn) -> None:
    """启用行级安全并重建租户隔离策略；owner 仍可 seed/写审计。"""
    with conn.cursor() as cur:
        for table in _RLS_TABLES:
            cur.execute(
                f"ALTER TABLE analytics.{table} ENABLE ROW LEVEL SECURITY"
            )
            cur.execute(
                f"DROP POLICY IF EXISTS tenant_isolation "
                f"ON analytics.{table}"
            )
            cur.execute(
                f"CREATE POLICY tenant_isolation ON analytics.{table} "
                "USING (tenant_id = "
                "current_setting('app.tenant_id', true))"
            )
        cur.execute(
            "ALTER TABLE analytics.order_items ENABLE ROW LEVEL SECURITY"
        )
        cur.execute(
            "DROP POLICY IF EXISTS tenant_isolation "
            "ON analytics.order_items"
        )
        cur.execute(
            "CREATE POLICY tenant_isolation ON analytics.order_items "
            "USING (EXISTS ("
            "SELECT 1 FROM analytics.orders o "
            "WHERE o.order_id = order_items.order_id "
            "AND o.tenant_id = "
            "current_setting('app.tenant_id', true)"
            "))"
        )


def _insert_batches(
    conn, sql: str, rows: Iterable[tuple], batch_size: int = 1000
) -> None:
    batch: list[tuple] = []
    with conn.cursor() as cur:
        for row in rows:
            batch.append(row)
            if len(batch) >= batch_size:
                cur.executemany(sql, batch)
                batch.clear()
        if batch:
            cur.executemany(sql, batch)


def _group_by_tenant(
    items: Sequence[Customer] | Sequence[Product],
) -> dict[str, list]:
    groups: dict[str, list] = {tenant: [] for tenant in TENANTS}
    for item in items:
        groups[item.tenant_id].append(item)
    return groups


def _generate_customers(
    rng: random.Random, fake: Faker, count: int
) -> list[Customer]:
    customers: list[Customer] = []
    emails: list[str] = []
    for index in range(count):
        # 前三个客户保证覆盖三个租户，便于小规模测试。
        tenant = TENANTS[index] if index < len(TENANTS) else _pick_tenant(rng)
        email = fake.email() if rng.random() > 0.05 else None
        if emails and rng.random() < 0.01:
            # 脏数据：少量重复邮箱。
            email = rng.choice(emails)
        if email:
            emails.append(email)
        customers.append(
            Customer(
                customer_id=f"cust-{index:06d}",
                tenant_id=tenant,
                name=fake.name(),
                email=email,
                phone=fake.phone_number() if rng.random() > 0.05 else None,
                region=rng.choice(REGIONS),
                segment=rng.choices(SEGMENTS, weights=(0.2, 0.3, 0.5), k=1)[0],
                created_at=_random_datetime(rng, 730),
            )
        )
    return customers


def _generate_products(
    rng: random.Random, count: int
) -> list[Product]:
    products: list[Product] = []
    for index in range(count):
        tenant = TENANTS[index] if index < len(TENANTS) else _pick_tenant(rng)
        category = rng.choice(CATEGORIES)
        products.append(
            Product(
                product_id=f"prod-{index:05d}",
                tenant_id=tenant,
                name=f"{category}商品{index:03d}",
                category=category,
                unit_price=_money(
                    Decimal(rng.randint(10, 5000)) + Decimal("0.90")
                ),
                active=rng.random() > 0.1,
            )
        )
    return products


def _generate_orders(
    rng: random.Random,
    customers_by_tenant: dict[str, list],
    products_by_tenant: dict[str, list],
    count: int,
) -> tuple[list[Order], list[tuple], dict[str, Decimal]]:
    all_customers = [
        customer
        for group in customers_by_tenant.values()
        for customer in group
    ]
    all_products = [
        product for group in products_by_tenant.values() for product in group
    ]
    orders: list[Order] = []
    order_items: list[tuple] = []
    totals: dict[str, Decimal] = {}

    for index in range(count):
        tenant = _pick_tenant(rng)
        customer = rng.choice(customers_by_tenant[tenant] or all_customers)
        order = Order(
            order_id=f"ord-{index:07d}",
            tenant_id=tenant,
            customer_id=customer.customer_id,
            order_date=_random_datetime(rng, 730),
            status=rng.choices(
                ORDER_STATUSES, weights=ORDER_STATUS_WEIGHTS, k=1
            )[0],
            channel=rng.choice(CHANNELS) if rng.random() > 0.03 else None,
            region=customer.region if rng.random() > 0.05 else None,
        )
        orders.append(order)

        candidates = products_by_tenant[tenant] or all_products
        chosen = rng.sample(
            candidates, k=min(rng.randint(1, 4), len(candidates))
        )
        total = Decimal("0")
        for product in chosen:
            quantity = rng.randint(1, 5)
            discount = Decimal(
                rng.choice(("0", "0.05", "0.10", "0.20", "0.30"))
            )
            total += product.unit_price * quantity * (Decimal("1") - discount)
            order_items.append(
                (
                    order.order_id,
                    product.product_id,
                    quantity,
                    product.unit_price,
                    discount,
                )
            )
        totals[order.order_id] = _money(total)
    return orders, order_items, totals


def _generate_refunds(
    rng: random.Random,
    orders: Sequence[Order],
    totals: dict[str, Decimal],
    count: int,
) -> list[tuple]:
    refunds: list[tuple] = []
    sample_size = min(count, len(orders))
    for index, order in enumerate(rng.sample(list(orders), k=sample_size)):
        total = totals[order.order_id]
        amount = _money(
            total * Decimal(str(round(rng.uniform(0.1, 1.0), 2)))
        )
        refund_date = min(
            order.order_date + timedelta(days=rng.randint(0, 30)),
            REFERENCE_DATE,
        )
        refunds.append(
            (
                f"ref-{index:06d}",
                order.tenant_id,
                order.order_id,
                refund_date,
                amount,
                rng.choice(REFUND_REASONS),
            )
        )
    return refunds


def _generate_subscriptions(
    rng: random.Random, customers: Sequence[Customer], count: int
) -> list[tuple]:
    subscriptions: list[tuple] = []
    for index in range(count):
        customer = rng.choice(customers)
        plan = rng.choices(PLANS, weights=(0.5, 0.35, 0.15), k=1)[0]
        start_date = _random_datetime(rng, 730).date()
        status = rng.choices(
            SUBSCRIPTION_STATUSES, weights=SUBSCRIPTION_WEIGHTS, k=1
        )[0]
        end_date = None
        if status != "active":
            end_date = min(
                start_date + timedelta(days=rng.randint(30, 365)),
                REFERENCE_DATE.date(),
            )
        subscriptions.append(
            (
                f"sub-{index:06d}",
                customer.tenant_id,
                customer.customer_id,
                plan,
                PLAN_PRICES[plan],
                start_date,
                end_date,
                status,
            )
        )
    return subscriptions


def _usage_rows(
    rng: random.Random, customers: Sequence[Customer], count: int
) -> Iterator[tuple]:
    for index in range(count):
        customer = rng.choice(customers)
        yield (
            f"evt-{index:09d}",
            customer.tenant_id,
            customer.customer_id,
            _random_datetime(rng, 365).date(),
            rng.choice(FEATURES),
            rng.randint(1, 1000),
        )


def _generate_tickets(
    rng: random.Random, customers: Sequence[Customer], count: int
) -> list[tuple]:
    tickets: list[tuple] = []
    for index in range(count):
        customer = rng.choice(customers)
        tickets.append(
            (
                f"tkt-{index:07d}",
                customer.tenant_id,
                customer.customer_id,
                _random_datetime(rng, 365),
                rng.choice(TICKET_CATEGORIES),
                rng.choices(
                    TICKET_STATUSES, weights=(0.1, 0.15, 0.5, 0.25), k=1
                )[0],
                rng.choices(
                    TICKET_PRIORITIES, weights=(0.4, 0.35, 0.2, 0.05), k=1
                )[0],
            )
        )
    return tickets


def _metric_rows() -> Iterator[tuple]:
    for tenant in TENANTS:
        for name, definition, expression in METRICS:
            yield (
                f"{tenant}:{name}",
                tenant,
                name,
                definition,
                expression,
                "v1",
            )


def seed_analytics(reset: bool = False, scale: float = 1.0) -> None:
    """生成合成数据；reset=True 先清空再重建，scale 控制数据规模。"""
    if scale <= 0:
        raise ValueError("scale 必须大于 0")

    rng = random.Random(42)
    fake = Faker("zh_CN")
    fake.seed_instance(42)

    with psycopg.connect(ANALYTICS_SEED_DATABASE_URL) as conn:
        _prepare_schema(conn)
        if reset:
            with conn.cursor() as cur:
                cur.execute(_TRUNCATE)

        customers = _generate_customers(
            rng, fake, _count(BASE_COUNTS["customers"], scale)
        )
        _insert_batches(
            conn,
            CUSTOMER_SQL,
            (
                (
                    customer.customer_id,
                    customer.tenant_id,
                    customer.name,
                    customer.email,
                    customer.phone,
                    customer.region,
                    customer.segment,
                    customer.created_at,
                )
                for customer in customers
            ),
        )

        products = _generate_products(
            rng, _count(BASE_COUNTS["products"], scale)
        )
        _insert_batches(
            conn,
            PRODUCT_SQL,
            (
                (
                    product.product_id,
                    product.tenant_id,
                    product.name,
                    product.category,
                    product.unit_price,
                    product.active,
                )
                for product in products
            ),
        )

        customers_by_tenant = _group_by_tenant(customers)
        products_by_tenant = _group_by_tenant(products)
        orders, order_items, totals = _generate_orders(
            rng,
            customers_by_tenant,
            products_by_tenant,
            _count(BASE_COUNTS["orders"], scale),
        )
        _insert_batches(
            conn,
            ORDER_SQL,
            (
                (
                    order.order_id,
                    order.tenant_id,
                    order.customer_id,
                    order.order_date,
                    order.status,
                    order.channel,
                    order.region,
                )
                for order in orders
            ),
        )
        _insert_batches(conn, ORDER_ITEM_SQL, order_items)

        _insert_batches(
            conn,
            REFUND_SQL,
            _generate_refunds(
                rng,
                orders,
                totals,
                _count(BASE_COUNTS["refunds"], scale),
            ),
        )
        _insert_batches(
            conn,
            SUBSCRIPTION_SQL,
            _generate_subscriptions(
                rng,
                customers,
                _count(BASE_COUNTS["subscriptions"], scale),
            ),
        )
        _insert_batches(
            conn,
            USAGE_SQL,
            _usage_rows(
                rng,
                customers,
                _count(BASE_COUNTS["usage_events"], scale),
            ),
        )
        _insert_batches(
            conn,
            TICKET_SQL,
            _generate_tickets(
                rng, customers, _count(BASE_COUNTS["tickets"], scale)
            ),
        )
        _insert_batches(conn, METRIC_SQL, _metric_rows())
        _ensure_rls(conn)
        conn.commit()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="生成 analytics 合成数据")
    parser.add_argument("--reset", action="store_true", help="先清空再重建")
    parser.add_argument(
        "--scale", type=float, default=1.0, help="数据规模系数"
    )
    args = parser.parse_args()
    seed_analytics(reset=args.reset, scale=args.scale)
