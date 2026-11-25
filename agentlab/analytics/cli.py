"""`agentlab-analytics`：数据分析 Agent 的命令行入口。"""

import argparse
import asyncio
import json

from agentlab.analytics.db import AnalyticsDB
from agentlab.analytics.graph import (
    build_analytics_graph,
    run_analytics_question,
)
from agentlab.analytics.session import AnalyticsSessionStore
from agentlab.analytics.versioning import build_model_router
from agentlab.config import ANALYTICS_TENANT_ID
from agentlab.models import build_chat_model
from agentlab.security.guard import redact_pii


def format_state(state: dict, max_rows: int = 20) -> str:
    """把一轮结果格式化成终端可读文本。"""
    result = state.get("result") or {}
    lines = []
    if state.get("clarification"):
        lines.append(f"需要澄清：{redact_pii(state['clarification'])}")
    if state.get("answer"):
        lines.append(redact_pii(str(state["answer"])))
    if state.get("sql"):
        lines.append(f"\nSQL：\n{redact_pii(str(state['sql']))}")
    columns = result.get("columns") or []
    rows = result.get("rows") or []
    if columns and rows:
        lines.append("\n" + " | ".join(map(str, columns)))
        for row in rows[:max_rows]:
            lines.append(" | ".join(str(value) for value in row))
        if result.get("truncated"):
            lines.append("...（结果已截断）")
    if state.get("chart_spec"):
        lines.append(
            "\nChart："
            + json.dumps(
                state["chart_spec"], ensure_ascii=False, default=str
            )
        )
    return "\n".join(lines) or "（没有结果）"


async def ask(
    question: str,
    *,
    tenant_id: str = ANALYTICS_TENANT_ID,
    session_id: str = "cli",
    user_id: str = "cli-user",
) -> dict:
    """执行一轮问答；CLI 会话进程内复用。"""
    graph = build_analytics_graph(
        build_chat_model(temperature=0),
        AnalyticsDB(),
        model_router=build_model_router(temperature=0),
    )
    sessions = AnalyticsSessionStore()
    state = await run_analytics_question(
        graph,
        question,
        tenant_id,
        user_id=user_id,
        conversation_context=sessions.context(user_id, session_id),
    )
    sessions.record(user_id, session_id, question, state)
    return state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentlab-analytics",
        description="对 Analytics 数仓提问（只读 SQL）",
    )
    parser.add_argument("question", help="自然语言问题")
    parser.add_argument(
        "--tenant", default=ANALYTICS_TENANT_ID, help="租户 ID"
    )
    parser.add_argument(
        "--session", default="cli", help="会话 ID（用于多轮上下文）"
    )
    parser.add_argument(
        "--json", action="store_true", help="输出完整 JSON 状态"
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        state = asyncio.run(
            ask(
                args.question,
                tenant_id=args.tenant,
                session_id=args.session,
            )
        )
    except Exception as exc:  # noqa: BLE001 - CLI 统一可读错误
        raise SystemExit(f"分析失败：{redact_pii(str(exc))}") from exc
    if args.json:
        print(
            json.dumps(state, ensure_ascii=False, indent=2, default=str)
        )
    else:
        print(format_state(state))


if __name__ == "__main__":
    main()
