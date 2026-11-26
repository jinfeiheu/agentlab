"""Analytics Agent 的 FastAPI 路由。"""

import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from agentlab.analytics.executor import cancel_task
from agentlab.analytics.graph import _audit_status, run_analytics_question
from agentlab.api.analytics.events import analytics_events
from agentlab.api.analytics.schemas import (
    AnalyticsCancelRequest,
    AnalyticsCancelResponse,
    AnalyticsChatRequest,
    AnalyticsChatResponse,
)
from agentlab.api.analytics.services import AnalyticsServices
from agentlab.api.deps import get_analytics_services, get_current_user
from agentlab.api.redaction import redact_value
from agentlab.api.streaming import _refusal_events
from agentlab.security.auth import UserContext
from agentlab.security.guard import check_input, redact_pii

logger = logging.getLogger(__name__)

router = APIRouter()


def _analytics_response(state: dict) -> AnalyticsChatResponse:
    result = state.get("result") or {}
    return AnalyticsChatResponse(
        answer=redact_pii(str(state.get("answer") or "")),
        sql=redact_pii(str(state.get("sql") or "")),
        columns=result.get("columns") or [],
        rows=redact_value(result.get("rows") or []),
        chart_spec=redact_value(state.get("chart_spec")),
        audit_id=str(state.get("request_id") or ""),
        clarification=redact_pii(
            str(state.get("clarification") or "")
        ),
        status=_audit_status(state),
    )


@router.post("/analytics/chat", response_model=AnalyticsChatResponse)
async def analytics_chat(
    request: Request,
    body: AnalyticsChatRequest,
    user: UserContext = Depends(get_current_user),
    svc: AnalyticsServices = Depends(get_analytics_services),
) -> AnalyticsChatResponse:
    if not request.app.state.limiter.allow(user.user_id):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    if body.tenant_id and body.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="tenant mismatch")
    decision = check_input(body.message)
    if not decision.allowed:
        return AnalyticsChatResponse(
            answer=decision.reason, status="refused_input"
        )
    key = f"{user.user_id}:{body.session_id}"
    context = svc.sessions.context(user.user_id, body.session_id)
    task = asyncio.current_task()
    request.app.state.analytics_tasks[key] = {
        "task": task,
        "request_id": "",
    }
    try:
        state = await asyncio.wait_for(
            run_analytics_question(
                svc.graph,
                body.message,
                user.tenant_id,
                user_id=user.user_id,
                conversation_context=context,
            ),
            timeout=request.app.state.request_timeout,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(
            status_code=504, detail="request timeout"
        ) from exc
    except asyncio.CancelledError as exc:
        raise HTTPException(
            status_code=499, detail="analytics cancelled"
        ) from exc
    except Exception as exc:  # noqa: BLE001 - 不泄漏堆栈
        logger.warning(
            "analytics chat failed: %s", redact_pii(str(exc))
        )
        raise HTTPException(
            status_code=500, detail="analytics failed"
        ) from exc
    finally:
        entry = request.app.state.analytics_tasks.get(key)
        if entry is not None and entry.get("task") is task:
            request.app.state.analytics_tasks.pop(key, None)
    svc.sessions.record(
        user.user_id, body.session_id, body.message, state
    )
    return _analytics_response(state)


@router.post("/analytics/chat/stream")
async def analytics_chat_stream(
    body: AnalyticsChatRequest,
    request: Request,
    user: UserContext = Depends(get_current_user),
    svc: AnalyticsServices = Depends(get_analytics_services),
) -> StreamingResponse:
    if not request.app.state.limiter.allow(user.user_id):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    if body.tenant_id and body.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="tenant mismatch")
    decision = check_input(body.message)
    if not decision.allowed:
        return StreamingResponse(
            _refusal_events(decision.reason),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    key = f"{user.user_id}:{body.session_id}"
    context = svc.sessions.context(user.user_id, body.session_id)
    request_id = uuid.uuid4().hex
    payload = {
        "question": body.message,
        "tenant_id": user.tenant_id,
        "request_id": request_id,
        "user_id": user.user_id,
        "conversation_context": context,
        "intent": {},
        "clarification": "",
        "sql": "",
        "sql_error": "",
        "repair_count": 0,
        "validation_failures": 0,
        "estimated_cost": 0.0,
        "approved": False,
        "rejected": False,
        "result": {},
        "answer": "",
        "chart_spec": None,
    }

    async def events():
        task = asyncio.current_task()
        request.app.state.analytics_tasks[key] = {
            "task": task,
            "request_id": request_id,
        }
        try:
            async for event in analytics_events(
                svc.graph,
                payload,
                {},
                svc.sessions,
                user.user_id,
                body.session_id,
                request,
            ):
                yield event
        finally:
            entry = request.app.state.analytics_tasks.get(key)
            if entry is not None and entry.get("task") is task:
                request.app.state.analytics_tasks.pop(key, None)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/analytics/cancel", response_model=AnalyticsCancelResponse
)
async def analytics_cancel(
    request: Request,
    body: AnalyticsCancelRequest,
    user: UserContext = Depends(get_current_user),
) -> AnalyticsCancelResponse:
    key = f"{user.user_id}:{body.session_id}"
    entry = request.app.state.analytics_tasks.get(key)
    if entry is None or entry["task"].done():
        return AnalyticsCancelResponse(
            cancelled=False, status="unknown"
        )
    cancel_task(str(entry.get("request_id") or ""))
    entry["task"].cancel()
    return AnalyticsCancelResponse(cancelled=True)
