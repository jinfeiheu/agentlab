"""FastAPI 服务:JWT 登录、健康检查与静态页。"""

import asyncio
import inspect
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from agentlab.api.analytics.routes import router as analytics_router
from agentlab.api.analytics.services import (
    AnalyticsServices,
    build_analytics_services,
)
from agentlab.api.auth_schemas import LoginRequest, LoginResponse
from agentlab.api.deps import RateLimiter
from agentlab.api.rag_agent.routes import router as rag_agent_router
from agentlab.api.rag_agent.services import Services, build_services
from agentlab.config import RATE_LIMIT_PER_MINUTE, REQUEST_TIMEOUT
from agentlab.security.auth import login as authenticate
from agentlab.security.guard import redact_pii
from agentlab.observability.tracing import setup_tracing, shutdown_tracing

STATIC_DIR = Path(__file__).resolve().parent / "static"

logger = logging.getLogger(__name__)


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
    app.include_router(analytics_router)

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
        return FileResponse(STATIC_DIR / "rag_agent.html")

    @app.get("/analytics", include_in_schema=False)
    def analytics_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "analytics.html")

    return app


app = create_app()


def serve() -> None:
    """用 uvicorn 启动 API；console script `agentlab-api` 的入口。"""
    import uvicorn

    uvicorn.run("agentlab.api.app:app", host="0.0.0.0", port=8000)
