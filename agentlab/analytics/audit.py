"""Analytics 审计写入：每次问答落一条记录，并对 PII 脱敏。"""

import psycopg

from agentlab.config import ANALYTICS_AUDIT_DATABASE_URL
from agentlab.security.guard import redact_pii

_INSERT = """
INSERT INTO analytics.analytics_audit
    (request_id, user_id, tenant_id, question, sql, status,
     row_count, estimated_cost, duration_ms, approved_by,
     prompt_version, model_id)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (request_id) DO UPDATE SET
    user_id = EXCLUDED.user_id,
    tenant_id = EXCLUDED.tenant_id,
    question = EXCLUDED.question,
    sql = EXCLUDED.sql,
    status = EXCLUDED.status,
    row_count = EXCLUDED.row_count,
    estimated_cost = EXCLUDED.estimated_cost,
    duration_ms = EXCLUDED.duration_ms,
    approved_by = EXCLUDED.approved_by,
    prompt_version = EXCLUDED.prompt_version,
    model_id = EXCLUDED.model_id
"""


async def write_audit(
    *,
    request_id: str,
    user_id: str,
    tenant_id: str,
    question: str,
    sql: str,
    status: str,
    row_count: int = 0,
    estimated_cost: float = 0.0,
    duration_ms: float = 0.0,
    approved_by: str | None = None,
    prompt_version: str | None = None,
    model_id: str | None = None,
) -> None:
    """写入审计记录；question/sql 先做 PII 脱敏。"""
    async with await psycopg.AsyncConnection.connect(
        ANALYTICS_AUDIT_DATABASE_URL
    ) as conn:
        await conn.execute(
            _INSERT,
            (
                request_id,
                user_id,
                tenant_id,
                redact_pii(question),
                redact_pii(sql),
                status,
                int(row_count),
                float(estimated_cost),
                int(round(duration_ms)),
                approved_by,
                prompt_version,
                model_id,
            ),
        )
