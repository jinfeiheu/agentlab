"""FastAPI 服务:JWT 登录、对话、SSE 流式输出与最小网页。"""

import asyncio
import inspect
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from agentlab.api.auth_schemas import LoginRequest, LoginResponse
from agentlab.api.deps import (
    RateLimiter,
    get_analytics_services,
    get_current_user,
)
from agentlab.api.rag_agent.routes import router as rag_agent_router
from agentlab.api.rag_agent.services import Services, build_services
from agentlab.api.redaction import redact_value
from agentlab.api.streaming import _refusal_events
from agentlab.security.auth import UserContext, login as authenticate
from agentlab.config import RATE_LIMIT_PER_MINUTE, REQUEST_TIMEOUT
from agentlab.api.analytics import (
    AnalyticsServices,
    analytics_events,
    build_analytics_services,
)
from agentlab.analytics.executor import cancel_task
from agentlab.analytics.graph import _audit_status, run_analytics_question
from agentlab.api.schemas import (
    AnalyticsCancelRequest,
    AnalyticsCancelResponse,
    AnalyticsChatRequest,
    AnalyticsChatResponse,
)
from agentlab.security.guard import check_input, redact_pii
from agentlab.observability.tracing import setup_tracing, shutdown_tracing

STATIC_DIR = Path(__file__).resolve().parent / "static"

logger = logging.getLogger(__name__)


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


def create_app(
    services: Services | None = None,
    analytics: AnalyticsServices | None = None,
) -> FastAPI:
    """创建 FastAPI 应用;传入 services/analytics 时跳过真实依赖构建。"""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        tracing_started = False
        try:
            if app.state.services is None:
                setup_tracing()
                tracing_started = True
                try:
                    app.state.services = await build_services()
                except Exception as exc:  # noqa: BLE001 - 启动失败降级为 503
                    logger.error("服务初始化失败: %s", redact_pii(str(exc)))
                    app.state.startup_error = (
                        f"服务初始化失败: {redact_pii(str(exc))}"
                    )
            if app.state.analytics is None:
                try:
                    app.state.analytics = build_analytics_services()
                except Exception as exc:  # noqa: BLE001 - Analytics 可独立降级
                    logger.error(
                        "Analytics 初始化失败: %s", redact_pii(str(exc))
                    )
            yield
        finally:
            current = app.state.services
            aclose = getattr(current, "aclose", None)
            if aclose is not None:
                await aclose()
            analytics_current = app.state.analytics
            analytics_close = getattr(analytics_current, "aclose", None)
            if analytics_close is not None:
                await analytics_close()
            if tracing_started:
                shutdown_tracing()

    app = FastAPI(title="Agent Interview Lab", lifespan=lifespan)
    app.state.services = services
    app.state.analytics = analytics
    app.state.startup_error = None
    app.state.limiter = RateLimiter(RATE_LIMIT_PER_MINUTE)
    app.state.request_timeout = REQUEST_TIMEOUT
    app.state.thread_locks: dict[str, asyncio.Lock] = {}
    app.state.analytics_tasks: dict[str, dict] = {}
    app.include_router(rag_agent_router)

    @app.post("/login", response_model=LoginResponse)
    def login_endpoint(body: LoginRequest) -> LoginResponse:
        token = authenticate(body.username, body.password)
        if token is None:
            raise HTTPException(
                status_code=401, detail="invalid username or password"
            )
        return LoginResponse(token=token)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        services = app.state.services
        if services is None:
            raise HTTPException(
                status_code=503,
                detail=getattr(app.state, "startup_error", "服务未就绪"),
            )
        check = getattr(services, "db_check", None)
        if check is not None:
            try:
                result = check()
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:  # noqa: BLE001 - 健康检查失败统一 503
                logger.warning(
                    "数据库健康检查失败: %s", redact_pii(str(exc))
                )
                raise HTTPException(
                    status_code=503, detail="数据库不可用"
                ) from exc
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/analytics", include_in_schema=False)
    def analytics_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "analytics.html")

    @app.post("/analytics/chat", response_model=AnalyticsChatResponse)
    async def analytics_chat(
        body: AnalyticsChatRequest,
        user: UserContext = Depends(get_current_user),
        svc: AnalyticsServices = Depends(get_analytics_services),
    ) -> AnalyticsChatResponse:
        if not app.state.limiter.allow(user.user_id):
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
        app.state.analytics_tasks[key] = {
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
                timeout=REQUEST_TIMEOUT,
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
            entry = app.state.analytics_tasks.get(key)
            if entry is not None and entry.get("task") is task:
                app.state.analytics_tasks.pop(key, None)
        svc.sessions.record(
            user.user_id, body.session_id, body.message, state
        )
        return _analytics_response(state)

    @app.post("/analytics/chat/stream")
    async def analytics_chat_stream(
        body: AnalyticsChatRequest,
        request: Request,
        user: UserContext = Depends(get_current_user),
        svc: AnalyticsServices = Depends(get_analytics_services),
    ) -> StreamingResponse:
        if not app.state.limiter.allow(user.user_id):
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
            app.state.analytics_tasks[key] = {
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
                entry = app.state.analytics_tasks.get(key)
                if entry is not None and entry.get("task") is task:
                    app.state.analytics_tasks.pop(key, None)

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post(
        "/analytics/cancel", response_model=AnalyticsCancelResponse
    )
    async def analytics_cancel(
        body: AnalyticsCancelRequest,
        user: UserContext = Depends(get_current_user),
    ) -> AnalyticsCancelResponse:
        key = f"{user.user_id}:{body.session_id}"
        entry = app.state.analytics_tasks.get(key)
        if entry is None or entry["task"].done():
            return AnalyticsCancelResponse(
                cancelled=False, status="unknown"
            )
        cancel_task(str(entry.get("request_id") or ""))
        entry["task"].cancel()
        return AnalyticsCancelResponse(cancelled=True)

    return app


app = create_app()


def serve() -> None:
    """用 uvicorn 启动 API；console script `agentlab-api` 的入口。"""
    import uvicorn

    uvicorn.run("agentlab.api.app:app", host="0.0.0.0", port=8000)
