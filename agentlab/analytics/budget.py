"""执行预算：步骤、token、成本、时间和并发。"""

import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class Budget:
    """一次分析任务的资源预算；consume 后由 exhausted 判断终止。"""

    max_steps: int = 6
    max_tokens: int = 100_000
    max_cost: float = 1.0
    deadline_s: float = 30.0
    max_concurrency: int = 3
    clock: Callable[[], float] = time.monotonic
    started_at: float | None = None
    steps: int = 0
    tokens: int = 0
    cost: float = 0.0

    def __post_init__(self) -> None:
        if self.started_at is None:
            self.started_at = self.clock()

    def consume(
        self,
        *,
        steps: int = 0,
        tokens: int = 0,
        cost: float = 0.0,
    ) -> None:
        self.steps += steps
        self.tokens += tokens
        self.cost += cost

    def exhausted(self) -> bool:
        return (
            self.steps >= self.max_steps
            or self.tokens >= self.max_tokens
            or self.cost >= self.max_cost
            or self.clock() - self.started_at >= self.deadline_s
        )
