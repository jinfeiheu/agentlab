"""用户私有工单:owner 校验,跨用户不泄露工单是否存在。"""

import hmac

from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime

from agentlab.config import DATABASE_URL
from agentlab.security.auth import UserContext


def can_access_ticket(ticket_user_id: str, current_user_id: str) -> bool:
    """工单 owner 与当前用户一致才允许访问;空身份一律拒绝。"""
    if not ticket_user_id or not current_user_id:
        return False
    return hmac.compare_digest(ticket_user_id, current_user_id)


def fetch_ticket(ticket_id: str) -> dict | None:
    """按 ID 查询工单;不存在返回 None。参数化查询,避免 SQL 注入。"""
    from psycopg import connect
    from psycopg.rows import dict_row

    with connect(DATABASE_URL, connect_timeout=3) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT ticket_id, user_id, subject, status "
                "FROM tickets WHERE ticket_id = %s",
                (ticket_id,),
            )
            row = cur.fetchone()
    return dict(row) if row else None


@tool
def get_ticket(ticket_id: str, runtime: ToolRuntime[UserContext]) -> str:
    """查询当前用户的工单详情;只能访问自己的工单。"""
    context = getattr(runtime, "context", None)
    current_user_id = getattr(context, "user_id", "")
    try:
        ticket = fetch_ticket(ticket_id)
    except Exception:  # noqa: BLE001 - 数据库错误不把堆栈返回给模型
        return "工单查询失败,请稍后再试。"
    if ticket is None or not can_access_ticket(
        ticket.get("user_id", ""), current_user_id
    ):
        # 未找到与无权限共用一句话,避免通过错误信息探测工单是否存在。
        return "未找到或无权限。"
    return (
        f"工单 {ticket['ticket_id']}: {ticket['subject']}"
        f"(状态:{ticket['status']})"
    )
