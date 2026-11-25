"""Analytics schema 与指标目录，供 SQL 守卫和 prompt 共用。"""

SCHEMA = {
    "customers_safe": (
        "customer_id, tenant_id, region, segment, created_at"
        "（脱敏视图，不含邮箱/电话）"
    ),
    "products": (
        "product_id, tenant_id, name, category, unit_price, active"
    ),
    "orders": (
        "order_id, tenant_id, customer_id, order_date, status,"
        " channel, region"
    ),
    "order_items": "order_id, product_id, quantity, unit_price, discount",
    "refunds": "refund_id, tenant_id, order_id, refund_date, amount, reason",
    "subscriptions": (
        "subscription_id, tenant_id, customer_id, plan, mrr,"
        " start_date, end_date, status"
    ),
    "usage_events": (
        "event_id, tenant_id, customer_id, event_date, feature, count"
    ),
    "tickets": (
        "ticket_id, tenant_id, customer_id, created_at, category,"
        " status, priority"
    ),
    "metric_catalog": (
        "metric_id, tenant_id, name, definition, sql_expression, version"
    ),
}

ALLOWED_RELATIONS = frozenset(SCHEMA)

METRICS = (
    (
        "revenue",
        "统计期内已完成订单的净收入（按 order_date，status='completed'）",
        "SUM(oi.quantity * oi.unit_price * (1 - oi.discount))",
    ),
    (
        "gmv",
        "统计期内所有订单的商品总额（按 order_date，含取消/退款）",
        "SUM(oi.quantity * oi.unit_price * (1 - oi.discount))",
    ),
    (
        "net_revenue",
        "统计期内已完成订单收入减去统计期内退款金额（退款按 refund_date）",
        "SUM(oi.quantity * oi.unit_price * (1 - oi.discount))"
        " - COALESCE(SUM(r.amount), 0)",
    ),
    (
        "refund_rate",
        "统计期内退款金额（按 refund_date）除以统计期内 GMV（按 order_date）",
        "COALESCE(SUM(r.amount), 0)"
        " / NULLIF(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 0)",
    ),
    (
        "active_customers",
        "统计期内有订单的去重客户数（任意订单状态）",
        "COUNT(DISTINCT o.customer_id)",
    ),
    (
        "order_count",
        "统计期内已完成订单数（status='completed'）",
        "COUNT(DISTINCT o.order_id)",
    ),
    (
        "aov",
        "统计期内已完成订单净收入除以已完成订单数",
        "SUM(oi.quantity * oi.unit_price * (1 - oi.discount))"
        " / NULLIF(COUNT(DISTINCT o.order_id), 0)",
    ),
    (
        "arpu",
        "统计期内已完成订单净收入除以去重客户数",
        "SUM(oi.quantity * oi.unit_price * (1 - oi.discount))"
        " / NULLIF(COUNT(DISTINCT o.customer_id), 0)",
    ),
    (
        "mrr",
        "统计期内有效订阅的 MRR 合计"
        "（仅按日期判断：start_date < 期末，且 end_date 为空或 >= 期初；"
        "不要额外用 status 过滤）",
        "SUM(mrr)",
    ),
)

METRIC_ALIASES = {
    "销售额": "revenue",
    "收入": "revenue",
    "成交总额": "gmv",
    "客单价": "aov",
    "退款率": "refund_rate",
    "活跃客户数": "active_customers",
    "订单数": "order_count",
    "月经常性收入": "mrr",
}

SCHEMA_BRIEF = "\n".join(
    f"- {table}: {columns}" for table, columns in SCHEMA.items()
)
METRIC_BRIEF = "\n".join(
    f"- {name}: {definition}；SQL: {expression}"
    for name, definition, expression in METRICS
) + "\n别名：" + "；".join(
    f"{alias} -> {name}" for alias, name in METRIC_ALIASES.items()
)
