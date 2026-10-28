"""FastAPI 服务:JWT 登录、对话、SSE 流式输出与最小网页。"""

import asyncio
import inspect
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from langgraph.types import Command

from agentlab.security.auth import UserContext, login as authenticate, verify_token
from agentlab.config import RATE_LIMIT_PER_MINUTE, REQUEST_TIMEOUT
from agentlab.api.schemas import (
    ChatRequest,
    ChatResponse,
    LoginRequest,
    LoginResponse,
    ResumeRequest,
)
from agentlab.api.services import (
    Services,
    _maybe_extract_memory,
    _prepare_thread,
    build_services,
)
from agentlab.api.sse import (
    _chat_events,
    _extract_answer,
    _extract_sources,
    _get_interrupt,
    _has_interrupt,
    _refusal_events,
)
from agentlab.security.guard import check_input, redact_pii
from agentlab.observability.tracing import setup_tracing, shutdown_tracing

STATIC_DIR = Path(__file__).resolve().parent / "static"

logger = logging.getLogger(__name__)


@dataclass
class RateLimiter:
    """按 user_id 的滑动窗口限流。"""

    limit: int
    window_seconds: float = 60.0
    hits: dict[str, list[float]] = field(default_factory=dict)

    def allow(self, user_id: str) -> bool:
        """记录一次请求;超过窗口上限返回 False。"""
        now = time.monotonic()
        recent = [
            stamp
            for stamp in self.hits.get(user_id, [])
            if now - stamp < self.window_seconds
        ]
        if len(recent) >= self.limit:
            self.hits[user_id] = recent
            return False
        recent.append(now)
        self.hits[user_id] = recent
        return True



def get_current_user(
    authorization: str | None = Header(default=None),
) -> UserContext:
    """从 Bearer token 解析用户身份;失败统一 401。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization[len("Bearer ") :].strip()
    try:
        user_id = verify_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc
    return UserContext(user_id=user_id)


def get_services(request: Request) -> Services:
    """从 app.state 取服务集合;启动失败时统一 503。"""
    services = request.app.state.services
    if services is None:
        raise HTTPException(
            status_code=503,
            detail=getattr(request.app.state, "startup_error", "服务未就绪"),
        )
    return services


def get_thread_lock(app: FastAPI, thread_id: str) -> asyncio.Lock:
    """同一 thread 的请求串行执行,避免 checkpoint 状态交错。"""
    locks = app.state.thread_locks
    lock = locks.get(thread_id)
    if lock is None:
        lock = asyncio.Lock()
        locks[thread_id] = lock
    return lock


def create_app(services: Services | None = None) -> FastAPI:
    """创建 FastAPI 应用;传入 services 时跳过真实依赖构建。"""

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
            yield
        finally:
            current = app.state.services
            aclose = getattr(current, "aclose", None)
            if aclose is not None:
                await aclose()
            if tracing_started:
                shutdown_tracing()

    app = FastAPI(title="Agent Interview Lab", lifespan=lifespan)
    app.state.services = services
    app.state.startup_error = None
    app.state.limiter = RateLimiter(RATE_LIMIT_PER_MINUTE)
    app.state.thread_locks: dict[str, asyncio.Lock] = {}

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

    @app.post("/chat", response_model=ChatResponse)
    async def chat(
        body: ChatRequest,
        user: UserContext = Depends(get_current_user),
        svc: Services = Depends(get_services),
    ) -> ChatResponse:
        if not app.state.limiter.allow(user.user_id):
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        decision = check_input(body.message)
        if not decision.allowed:
            return ChatResponse(answer=decision.reason, sources=[])
        thread_id = f"{user.user_id}:{body.session_id}"
        config = {"configurable": {"thread_id": thread_id}}
        async with get_thread_lock(app, thread_id):
            try:
                await asyncio.wait_for(
                    _prepare_thread(svc.graph, config),
                    timeout=REQUEST_TIMEOUT,
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
                    timeout=REQUEST_TIMEOUT,
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
                    timeout=min(REQUEST_TIMEOUT, 10),
                )
            except asyncio.TimeoutError:
                logger.warning("非流式轮次结束后记忆抽取超时,已跳过")
        return ChatResponse(
            answer=_extract_answer(result),
            sources=_extract_sources(result),
            interrupt=interrupt,
        )

    @app.post("/chat/resume", response_model=ChatResponse)
    async def chat_resume(
        body: ResumeRequest,
        user: UserContext = Depends(get_current_user),
        svc: Services = Depends(get_services),
    ) -> ChatResponse:
        """恢复 pending interrupt;没有中断时返回 409。"""
        if not app.state.limiter.allow(user.user_id):
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        thread_id = f"{user.user_id}:{body.session_id}"
        config = {"configurable": {"thread_id": thread_id}}
        async with get_thread_lock(app, thread_id):
            aget_state = getattr(svc.graph, "aget_state", None)
            if aget_state is None:
                raise HTTPException(
                    status_code=409, detail="no pending interrupt"
                )
            try:
                state = await asyncio.wait_for(
                    aget_state(config), timeout=REQUEST_TIMEOUT
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
                    timeout=REQUEST_TIMEOUT,
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

    @app.post("/chat/stream/resume")
    async def chat_stream_resume(
        body: ResumeRequest,
        request: Request,
        user: UserContext = Depends(get_current_user),
        svc: Services = Depends(get_services),
    ) -> StreamingResponse:
        """流式恢复 pending interrupt;没有中断时返回 409。"""
        if not app.state.limiter.allow(user.user_id):
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        thread_id = f"{user.user_id}:{body.session_id}"
        config = {"configurable": {"thread_id": thread_id}}
        try:
            has_interrupt = await asyncio.wait_for(
                _has_interrupt(svc.graph, config), timeout=REQUEST_TIMEOUT
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
                REQUEST_TIMEOUT,
                get_thread_lock(app, thread_id),
                context=user,
                services=svc,
                skip_prepare=True,
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/chat/stream")
    async def chat_stream(
        body: ChatRequest,
        request: Request,
        user: UserContext = Depends(get_current_user),
        svc: Services = Depends(get_services),
    ) -> StreamingResponse:
        if not app.state.limiter.allow(user.user_id):
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
                REQUEST_TIMEOUT,
                get_thread_lock(app, thread_id),
                context=user,
                services=svc,
                user_text=body.message,
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


app = create_app()


def serve() -> None:
    """用 uvicorn 启动 API；console script `agentlab-api` 的入口。"""
    import uvicorn

    uvicorn.run("agentlab.api.app:app", host="0.0.0.0", port=8000)
