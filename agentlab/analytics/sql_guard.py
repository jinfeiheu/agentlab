"""SQL 安全守卫：只允许单条只读 SELECT。

这是三层防御中的第一层；执行层还有只读角色和 RLS。
"""

from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

DEFAULT_LIMIT = 200
MAX_LIMIT = 1000

# 只允许访问 analytics schema；空 schema 表示依赖连接的 search_path。
ALLOWED_SCHEMAS = {"analytics"}
SYSTEM_SCHEMAS = {"pg_catalog", "information_schema", "pg_toast", "pg_temp"}

_FORBIDDEN_NODES = tuple(
    getattr(exp, name)
    for name in (
        "Insert",
        "Update",
        "Delete",
        "Create",
        "Drop",
        "Alter",
        "Copy",
        "Set",
        "Command",
        "Transaction",
        "Commit",
        "Rollback",
        "Grant",
        "Revoke",
        "TruncateTable",
        "Merge",
    )
    if hasattr(exp, name)
)


@dataclass(frozen=True)
class ValidationResult:
    """守卫结果；拒绝时 reason 说明原因。"""

    allowed: bool
    reason: str = ""
    normalized_sql: str = ""


def _reject(reason: str, sql: str) -> ValidationResult:
    """构造拒绝结果，保留原始 SQL 方便审计。"""
    return ValidationResult(allowed=False, reason=reason, normalized_sql=sql)


def validate_sql(sql: str, allowed_relations: set[str]) -> ValidationResult:
    """校验只读 SQL，必要时补 LIMIT 并返回规范化语句。"""
    if not sql or not sql.strip():
        return _reject("SQL 不能为空", sql)

    try:
        statements = sqlglot.parse(sql, read="postgres")
    except ParseError as exc:
        return _reject(f"SQL 解析失败：{exc}", sql)

    statements = [
        statement for statement in statements if statement is not None
    ]
    if len(statements) != 1:
        return _reject("只允许单条 SQL 语句", sql)

    root = statements[0]
    if not isinstance(root, exp.Select):
        return _reject(
            f"只允许 SELECT 查询，实际为 {type(root).__name__}", sql
        )

    # CTE 里的 DML 也必须拒绝，不能只看根节点。
    for node in root.walk():
        if isinstance(node, _FORBIDDEN_NODES):
            return _reject(f"禁止的 SQL 操作：{type(node).__name__}", sql)

    allowed = {name.lower() for name in allowed_relations}
    cte_names = {
        cte.alias_or_name.lower() for cte in root.find_all(exp.CTE)
    }
    for table in root.find_all(exp.Table):
        schema = (table.db or "").lower()
        name = (table.name or "").lower()
        # CTE 引用不是物理表，跳过 allowlist 检查。
        if not schema and name in cte_names:
            continue
        if schema in SYSTEM_SCHEMAS:
            return _reject(f"禁止访问系统 schema：{schema}", sql)
        if schema and schema not in ALLOWED_SCHEMAS:
            return _reject(f"禁止访问 schema：{schema}", sql)
        if name not in allowed:
            return _reject(f"禁止访问未授权的表：{name}", sql)

    limit = root.args.get("limit")
    if limit is None:
        root = root.limit(DEFAULT_LIMIT)
    else:
        limit_value = limit.expression
        if not (
            isinstance(limit_value, exp.Literal) and limit_value.is_int
        ):
            root = root.limit(MAX_LIMIT)
        elif int(limit_value.this) > MAX_LIMIT:
            root = root.limit(MAX_LIMIT)

    return ValidationResult(
        allowed=True,
        reason="",
        normalized_sql=root.sql(dialect="postgres"),
    )
