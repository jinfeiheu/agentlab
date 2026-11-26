"""RAG Agent 的 FastAPI 路由。"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langgraph.types import Command

from agentlab.api.deps import get_current_user, get_services, get_thread_lock
from agentlab.api.rag_agent.schemas import (
    ChatRequest,
    ChatResponse,
    ResumeRequest,
)
from agentlab.api.rag_agent.services import (
    Services,
    _maybe_extract_memory,
    _prepare_thread,
)
from agentlab.api.rag_agent.sse import (
    _chat_events,
    _extract_answer,
    _extract_sources,
    _get_interrupt,
    _has_interrupt,
)
from agentlab.api.streaming import _refusal_events
from agentlab.security.auth import UserContext
from agentlab.security.guard import check_input

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    body: ChatRequest,
    user: UserContext = Depends(get_current_user),
    svc: Services = Depends(get_services),
) -> ChatResponse:
    if not request.app.state.limiter.allow(user.user_id):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    decision = check_input(body.message)
    if not decision.allowed:
        return ChatResponse(answer=decision.reason, sources=[])
    thread_id = f"{user.user_id}:{body.session_id}"
    config = {"configurable": {"thread_id": thread_id}}
    async with get_thread_lock(request.app, thread_id):
        try:
            await asyncio.wait_for(
                _prepare_thread(svc.graph, config),
                timeout=request.app.state.request_timeout,
            )
        except asyncio.TimeoutError as exc:
            raise HTTPException(
                status_code=504, detail="request timeout"
            ) from exc
        try:
            result = await asyncio.wait_for(
                svc.graph.ainvoke(
                    {"messages": [("user", body.message)]},
                    config=config,
                    context=user,
                ),
                timeout=request.app.state.request_timeout,
            )
        except asyncio.TimeoutError as exc:
            raise HTTPException(
                status_code=504, detail="request timeout"
            ) from exc
        except Exception as exc:  # noqa: BLE001 - 统一成 500,避免泄漏堆栈
            raise HTTPException(
                status_code=500, detail="chat failed"
            ) from exc
        interrupt = await _get_interrupt(svc.graph, config)
    if interrupt is None:
        try:
            await asyncio.wait_for(
                _maybe_extract_memory(
                    svc, user, body.message, result.get("messages", [])
                ),
                timeout=min(request.app.state.request_timeout, 10),
            )
        except asyncio.TimeoutError:
            logger.warning("非流式轮次结束后记忆抽取超时,已跳过")
    return ChatResponse(
        answer=_extract_answer(result),
        sources=_extract_sources(result),
        interrupt=interrupt,
    )


@router.post("/chat/resume", response_model=ChatResponse)
async def chat_resume(
    request: Request,
    body: ResumeRequest,
    user: UserContext = Depends(get_current_user),
    svc: Services = Depends(get_services),
) -> ChatResponse:
    """恢复 pending interrupt;没有中断时返回 409。"""
    if not request.app.state.limiter.allow(user.user_id):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    thread_id = f"{user.user_id}:{body.session_id}"
    config = {"configurable": {"thread_id": thread_id}}
    async with get_thread_lock(request.app, thread_id):
        aget_state = getattr(svc.graph, "aget_state", None)
        if aget_state is None:
            raise HTTPException(
                status_code=409, detail="no pending interrupt"
            )
        try:
            state = await asyncio.wait_for(
                aget_state(config),
                timeout=request.app.state.request_timeout,
            )
        except asyncio.TimeoutError as exc:
            raise HTTPException(
                status_code=504, detail="request timeout"
            ) from exc
        if not getattr(state, "interrupts", ()):
            raise HTTPException(
                status_code=409, detail="no pending interrupt"
            )
        try:
            result = await asyncio.wait_for(
                svc.graph.ainvoke(
                    Command(resume=body.answer),
                    config=config,
                    context=user,
                ),
                timeout=request.app.state.request_timeout,
            )
        except asyncio.TimeoutError as exc:
            raise HTTPException(
                status_code=504, detail="request timeout"
            ) from exc
        except Exception as exc:  # noqa: BLE001 - 统一成 500
            raise HTTPException(
                status_code=500, detail="resume failed"
            ) from exc
        interrupt = await _get_interrupt(svc.graph, config)
    return ChatResponse(
        answer=_extract_answer(result),
        sources=_extract_sources(result),
        interrupt=interrupt,
    )


@router.post("/chat/stream/resume")
async def chat_stream_resume(
    body: ResumeRequest,
    request: Request,
    user: UserContext = Depends(get_current_user),
    svc: Services = Depends(get_services),
) -> StreamingResponse:
    """流式恢复 pending interrupt;没有中断时返回 409。"""
    if not request.app.state.limiter.allow(user.user_id):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    thread_id = f"{user.user_id}:{body.session_id}"
    config = {"configurable": {"thread_id": thread_id}}
    try:
        has_interrupt = await asyncio.wait_for(
            _has_interrupt(svc.graph, config),
            timeout=request.app.state.request_timeout,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(
            status_code=504, detail="request timeout"
        ) from exc
    if not has_interrupt:
        raise HTTPException(status_code=409, detail="no pending interrupt")
    return StreamingResponse(
        _chat_events(
            svc.graph,
            Command(resume=body.answer),
            config,
            request,
            request.app.state.request_timeout,
            get_thread_lock(request.app, thread_id),
            context=user,
            services=svc,
            skip_prepare=True,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat/stream")
async def chat_stream(
    body: ChatRequest,
    request: Request,
    user: UserContext = Depends(get_current_user),
    svc: Services = Depends(get_services),
) -> StreamingResponse:
    if not request.app.state.limiter.allow(user.user_id):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
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
    thread_id = f"{user.user_id}:{body.session_id}"
    config = {"configurable": {"thread_id": thread_id}}
    return StreamingResponse(
        _chat_events(
            svc.graph,
            {"messages": [("user", body.message)]},
            config,
            request,
            request.app.state.request_timeout,
            get_thread_lock(request.app, thread_id),
            context=user,
            services=svc,
            user_text=body.message,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
