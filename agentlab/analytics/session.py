"""多轮分析会话：复用上一轮指标/维度/时间范围，并做上下文压缩。"""

from dataclasses import dataclass, field

from agentlab.config import ANALYTICS_SESSION_MAX_CHARS


@dataclass
class Turn:
    """一轮分析的可复用上下文。"""

    question: str
    metrics: list[str] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    time_range: str = ""
    sql: str = ""
    answer: str = ""

    def render(self) -> str:
        parts = [f"问题：{self.question}"]
        if self.metrics:
            parts.append(f"指标：{', '.join(self.metrics)}")
        if self.dimensions:
            parts.append(f"维度：{', '.join(self.dimensions)}")
        if self.time_range:
            parts.append(f"时间：{self.time_range}")
        return "；".join(parts)


class AnalyticsSession:
    """单个用户会话；按 user_id:session_id 隔离。"""

    def __init__(self, max_chars: int = ANALYTICS_SESSION_MAX_CHARS):
        self.max_chars = max(1, int(max_chars))
        self.turns: list[Turn] = []

    def record(
        self,
        question: str,
        state: dict,
        answer: str | None = None,
    ) -> None:
        intent = state.get("intent") or {}
        self.turns.append(
            Turn(
                question=question,
                metrics=[
                    str(item)
                    for item in (intent.get("metrics") or [])
                    if item
                ],
                dimensions=[
                    str(item)
                    for item in (intent.get("dimensions") or [])
                    if item
                ],
                time_range=str(intent.get("time_range") or ""),
                sql=str(state.get("sql") or ""),
                answer=str(answer or state.get("answer") or "")[:300],
            )
        )

    def context(self) -> str:
        """渲染最近轮次；超预算时丢最旧轮次，仍超则截断。"""
        if not self.turns:
            return ""
        header = (
            "历史分析上下文（最近优先；本轮未明确覆盖指标/维度/时间时复用）：\n"
        )
        selected: list[str] = []
        used = len(header)
        for index, turn in enumerate(reversed(self.turns), start=1):
            line = f"{index}. {turn.render()}\n"
            if used + len(line) > self.max_chars:
                break
            selected.append(line)
            used += len(line)
        if not selected:
            # 单轮也超预算：截断最近一轮。
            latest = self.turns[-1].render()
            return (header + latest)[: self.max_chars]
        return header + "".join(selected)

    def reset(self) -> None:
        self.turns.clear()


class AnalyticsSessionStore:
    """进程内会话表；生产可替换为 Redis/Postgres。"""

    def __init__(self, max_chars: int = ANALYTICS_SESSION_MAX_CHARS):
        self.max_chars = max_chars
        self._sessions: dict[str, AnalyticsSession] = {}

    @staticmethod
    def key(user_id: str, session_id: str) -> str:
        return f"{user_id}:{session_id}"

    def get(self, user_id: str, session_id: str) -> AnalyticsSession:
        key = self.key(user_id, session_id)
        session = self._sessions.get(key)
        if session is None:
            session = AnalyticsSession(max_chars=self.max_chars)
            self._sessions[key] = session
        return session

    def context(self, user_id: str, session_id: str) -> str:
        return self.get(user_id, session_id).context()

    def record(
        self, user_id: str, session_id: str, question: str, state: dict
    ) -> None:
        self.get(user_id, session_id).record(question, state)

    def reset(self, user_id: str, session_id: str) -> None:
        self.get(user_id, session_id).reset()

    def count(self) -> int:
        return len(self._sessions)
