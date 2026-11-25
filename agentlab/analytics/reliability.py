"""Analytics 可靠性工具：超时、重试、熔断。"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class AnalyticsTimeoutError(RuntimeError):
    """模型或外部调用超时。"""


class CircuitOpenError(RuntimeError):
    """熔断器打开，拒绝请求。"""


async def run_with_timeout(
    awaitable: Awaitable[T], timeout_s: float, label: str
) -> T:
    """等待协程，超时抛可读错误。"""
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout_s)
    except asyncio.TimeoutError as exc:
        raise AnalyticsTimeoutError(
            f"{label} 超时（{timeout_s}s）"
        ) from exc


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    attempts: int = 2,
    base_delay: float = 0.0,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    """指数退避重试；用尽后抛最后一次异常。"""
    if attempts < 1:
        raise ValueError("attempts 必须大于 0")
    for attempt in range(attempts):
        try:
            return await operation()
        except retry_on:
            if attempt == attempts - 1:
                raise
            if base_delay > 0:
                await asyncio.sleep(base_delay * (2**attempt))
    raise RuntimeError("unreachable")  # pragma: no cover


class CircuitBreaker:
    """简单 closed / open / half-open 熔断器。"""

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout_s: float = 30.0,
        clock=time.monotonic,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout_s = reset_timeout_s
        self._clock = clock
        self._failures = 0
        self._opened_at = 0.0
        self._state = "closed"

    @property
    def state(self) -> str:
        return self._state

    def allow_request(self) -> bool:
        if self._state == "open":
            if self._clock() - self._opened_at >= self.reset_timeout_s:
                self._state = "half_open"
                return True
            return False
        return True

    def record_success(self) -> None:
        self._failures = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failures += 1
        if (
            self._state == "half_open"
            or self._failures >= self.failure_threshold
        ):
            self._state = "open"
            self._opened_at = self._clock()
