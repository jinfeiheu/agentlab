"""Analytics 只读数据库访问：连接、租户上下文、超时与行数限制。"""

import json
import time
from dataclasses import dataclass

import psycopg
from psycopg import sql

from agentlab.config import ANALYTICS_DATABASE_URL
from agentlab.security.guard import redact_pii


class AnalyticsDBError(RuntimeError):
    """数据库访问失败；调用方只依赖这个异常类型。"""


@dataclass(frozen=True)
class QueryResult:
    """一次查询的结果。"""

    columns: list[str]
    rows: list[tuple]
    row_count: int
    truncated: bool
    duration_ms: float


class AnalyticsDB:
    """只读 Analytics 连接；每次查询新建连接，避免跨租户复用。"""

    def __init__(self, dsn: str = ANALYTICS_DATABASE_URL) -> None:
        self._dsn = dsn

    async def _run_sql(
        self,
        sql_text: str,
        tenant_id: str,
        max_rows: int,
        timeout_ms: int,
    ) -> tuple[list[str], list[tuple], float]:
        """在只读事务中执行 SQL，返回列、行和耗时。"""
        started = time.perf_counter()
        try:
            async with await psycopg.AsyncConnection.connect(
                self._dsn, connect_timeout=3
            ) as conn:
                async with conn.transaction():
                    # SET 不接受参数占位符，用 Literal 拼接并保证转义。
                    await conn.execute(
                        sql.SQL("SET LOCAL statement_timeout = {}").format(
                            sql.Literal(int(timeout_ms))
                        )
                    )
                    await conn.execute(
                        sql.SQL("SET LOCAL app.tenant_id = {}").format(
                            sql.Literal(tenant_id)
                        )
                    )
                    await conn.execute(
                        "SET LOCAL search_path TO analytics, public"
                    )
                    async with conn.cursor() as cursor:
                        await cursor.execute(sql_text)
                        columns = [
                            column.name
                            for column in (cursor.description or [])
                        ]
                        rows = await cursor.fetchmany(max_rows + 1)
        except AnalyticsDBError:
            raise
        except Exception as exc:
            # 错误信息可能回显 SQL 字面量，先做 PII 脱敏再包装。
            raise AnalyticsDBError(
                f"查询执行失败：{redact_pii(str(exc))}"
            ) from exc
        return columns, rows, (time.perf_counter() - started) * 1000

    async def execute(
        self,
        sql_text: str,
        tenant_id: str,
        max_rows: int = 200,
        timeout_ms: int = 5000,
    ) -> QueryResult:
        """在只读事务中执行 SQL，并强制超时与行数上限。"""
        max_rows = max(0, int(max_rows))
        columns, rows, duration_ms = await self._run_sql(
            sql_text, tenant_id, max_rows, timeout_ms
        )
        truncated = len(rows) > max_rows
        visible_rows = rows[:max_rows]
        return QueryResult(
            columns=columns,
            rows=visible_rows,
            row_count=len(visible_rows),
            truncated=truncated,
            duration_ms=duration_ms,
        )

    async def explain(
        self, sql_text: str, tenant_id: str, timeout_ms: int = 5000
    ) -> float:
        """用 EXPLAIN (FORMAT JSON) 估算查询总成本。"""
        _columns, rows, _duration = await self._run_sql(
            f"EXPLAIN (FORMAT JSON) {sql_text}",
            tenant_id,
            max_rows=1,
            timeout_ms=timeout_ms,
        )
        if not rows:
            return 0.0
        payload = rows[0][0]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                return 0.0
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        if not isinstance(payload, dict):
            return 0.0
        plan = payload.get("Plan") or {}
        try:
            return float(plan.get("Total Cost", 0.0))
        except (TypeError, ValueError):
            return 0.0
