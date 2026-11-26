"""Analytics API 的 SSE 计划事件。"""

import asyncio
import time

from agentlab.analytics.audit import write_audit
from agentlab.analytics.graph import _audit_status, _summarize
from agentlab.analytics.session import AnalyticsSessionStore
from agentlab.api.redaction import redact_value
from agentlab.api.streaming import sse
from agentlab.security.guard import redact_pii

DEFAULT_STEPS = [
    "understand",
    "plan_sql",
    "validate_sql",
    "estimate_cost",
    "approve",
    "execute",
    "answer",
]


def _step_summary(node: str, data: dict) -> dict:
    summary: dict = {}
    if "sql" in data:
        summary["sql_chars"] = len(str(data.get("sql") or ""))
    if "sql_error" in data:
        summary["error"] = redact_pii(str(data.get("sql_error") or ""))
    if "estimated_cost" in data:
        summary["estimated_cost"] = data.get("estimated_cost")
    if "repair_count" in data:
        summary["repair_count"] = data.get("repair_count")
    result = data.get("result") or {}
    if result:
        summary["row_count"] = result.get("row_count", 0)
    return summary


async def _audit_stream(
    state: dict,
    payload: dict,
    status: str,
    duration_ms: float,
    user_id: str,
) -> None:
    result = state.get("result") or {}
    await write_audit(
        request_id=str(payload.get("request_id") or ""),
        user_id=user_id,
        tenant_id=str(payload.get("tenant_id") or ""),
        question=str(payload.get("question") or ""),
        sql=str(state.get("sql") or ""),
        status=status,
        row_count=result.get("row_count", 0),
        estimated_cost=float(state.get("estimated_cost", 0.0) or 0.0),
        duration_ms=duration_ms,
        prompt_version=_summarize(state.get("prompt_versions")),
        model_id=_summarize(state.get("model_ids")),
    )


async def analytics_events(
    graph,
    payload: dict,
    config: dict,
    sessions: AnalyticsSessionStore,
    user_id: str,
    session_id: str,
    request=None,
):
    """把图更新映射成 plan_created/step_*/verification/replan/final 事件。"""
    request_id = str(payload.get("request_id") or "")
    state = dict(payload)
    started = time.perf_counter()
    yield sse(
        {
            "type": "plan_created",
            "steps": DEFAULT_STEPS,
            "audit_id": request_id,
        }
    )
    try:
        astream = getattr(graph, "astream", None)
        if astream is None:
            state.update(await graph.ainvoke(payload, config=config))
        else:
            async for update in graph.astream(
                payload, config=config, stream_mode="updates"
            ):
                if request is not None and await request.is_disconnected():
                    await _audit_stream(
                        state,
                        payload,
                        "cancelled",
                        (time.perf_counter() - started) * 1000,
                        user_id,
                    )
                    return
                for node, data in (update or {}).items():
                    if not isinstance(data, dict):
                        continue
                    state.update(data)
                    yield sse({"type": "step_started", "step": node})
                    yield sse(
                        {
                            "type": "step_result",
                            "step": node,
                            **_step_summary(node, data),
                        }
                    )
                    if node == "validate_sql":
                        yield sse(
                            {
                                "type": "verification",
                                "ok": not data.get("sql_error"),
                                "reason": redact_pii(
                                    str(data.get("sql_error") or "")
                                ),
                            }
                        )
                    if node == "repair":
                        yield sse(
                            {
                                "type": "replan",
                                "repair_count": data.get(
                                    "repair_count", 0
                                ),
                            }
                        )
    except asyncio.CancelledError:
        try:
            await _audit_stream(
                state,
                payload,
                "cancelled",
                (time.perf_counter() - started) * 1000,
                user_id,
            )
        except Exception:  # noqa: BLE001 - 取消路径尽力写审计
            pass
        yield sse({"type": "error", "message": "cancelled"})
        return
    except Exception as exc:  # noqa: BLE001 - 流内错误统一事件
        yield sse({"type": "error", "message": redact_pii(str(exc))})
        return

    duration_ms = (time.perf_counter() - started) * 1000
    result = state.get("result") or {}
    status = _audit_status(state)
    await _audit_stream(state, payload, status, duration_ms, user_id)
    sessions.record(
        user_id,
        session_id,
        str(payload.get("question") or ""),
        state,
    )
    yield sse(
        {
            "type": "final",
            "answer": redact_pii(str(state.get("answer") or "")),
            "sql": redact_pii(str(state.get("sql") or "")),
            "columns": result.get("columns") or [],
            "rows": redact_value(result.get("rows") or []),
            "chart_spec": redact_value(state.get("chart_spec")),
            "audit_id": request_id,
            "clarification": redact_pii(
                str(state.get("clarification") or "")
            ),
            "status": status,
        }
    )
