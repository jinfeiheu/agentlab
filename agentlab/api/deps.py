"""FastAPI 共享依赖：鉴权、服务访问、限流与线程锁。"""

import asyncio
import time
from dataclasses import dataclass, field

from fastapi import FastAPI, Header, HTTPException, Request

from agentlab.api.analytics import AnalyticsServices
from agentlab.api.rag_agent.services import Services
from agentlab.security.auth import UserContext, tenant_for_user, verify_token


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
    return UserContext(
        user_id=user_id, tenant_id=tenant_for_user(user_id)
    )


def get_services(request: Request) -> Services:
    """从 app.state 取服务集合;启动失败时统一 503。"""
    services = request.app.state.services
    if services is None:
        raise HTTPException(
            status_code=503,
            detail=getattr(request.app.state, "startup_error", "服务未就绪"),
        )
    return services


def get_analytics_services(request: Request) -> AnalyticsServices:
    """从 app.state 取 Analytics 服务；未初始化时 503。"""
    services = request.app.state.analytics
    if services is None:
        raise HTTPException(status_code=503, detail="analytics 未就绪")
    return services


def get_thread_lock(app: FastAPI, thread_id: str) -> asyncio.Lock:
    """同一 thread 的请求串行执行,避免 checkpoint 状态交错。"""
    locks = app.state.thread_locks
    lock = locks.get(thread_id)
    if lock is None:
        lock = asyncio.Lock()
        locks[thread_id] = lock
    return lock
