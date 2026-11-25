"""token、成本与延迟指标。"""

import math
import statistics
from dataclasses import dataclass, field

# 价格单位:每 100 万 token 的输入/输出价格(人民币元)。
DEFAULT_PRICES: dict[str, tuple[float, float]] = {
    "deepseek-flash": (2.0, 8.0),
}


@dataclass
class Usage:
    """一次模型调用的 token 用量。"""

    input_tokens: int
    output_tokens: int
    total_tokens: int


def usage_from_message(message) -> Usage:
    """从 LangChain 消息中读取 token 用量,兼容两种元数据格式。"""
    metadata = getattr(message, "usage_metadata", None) or {}
    if metadata:
        input_tokens = int(metadata.get("input_tokens", 0) or 0)
        output_tokens = int(metadata.get("output_tokens", 0) or 0)
        total_tokens = int(
            metadata.get("total_tokens", 0) or input_tokens + output_tokens
        )
        return Usage(input_tokens, output_tokens, total_tokens)

    response_metadata = getattr(message, "response_metadata", None) or {}
    token_usage = response_metadata.get("token_usage", {}) or {}
    input_tokens = int(token_usage.get("prompt_tokens", 0) or 0)
    output_tokens = int(token_usage.get("completion_tokens", 0) or 0)
    total_tokens = int(
        token_usage.get("total_tokens", 0) or input_tokens + output_tokens
    )
    return Usage(input_tokens, output_tokens, total_tokens)


def estimate_cost(
    usage: Usage,
    model: str,
    prices: dict[str, tuple[float, float]] | None = None,
) -> float:
    """按每百万 token 的价格估算单次调用成本。"""
    table = prices or DEFAULT_PRICES
    if model not in table:
        raise ValueError(f"没有模型 {model} 的价格")
    input_price, output_price = table[model]
    return (
        usage.input_tokens * input_price + usage.output_tokens * output_price
    ) / 1_000_000


def _p95(latencies: list[float]) -> float:
    """nearest-rank 的 P95。"""
    if not latencies:
        return 0.0
    ordered = sorted(latencies)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return float(ordered[min(index, len(ordered) - 1)])


@dataclass
class MetricsRecorder:
    """记录每次调用的延迟和 token 用量,汇总为报告指标。"""

    model: str = "deepseek-flash"
    records: list[tuple[str, float, Usage | None]] = field(default_factory=list)

    def record(
        self,
        name: str,
        latency_ms: float,
        usage: Usage | None = None,
    ) -> None:
        self.records.append((name, latency_ms, usage))

    def summary(self) -> dict[str, float]:
        latencies = [latency for _, latency, _ in self.records]
        usages = [usage for _, _, usage in self.records if usage is not None]
        return {
            "count": len(self.records),
            "p50_ms": float(statistics.median(latencies)) if latencies else 0.0,
            "p95_ms": _p95(latencies),
            "total_tokens": sum(usage.total_tokens for usage in usages),
            "total_cost": sum(
                estimate_cost(usage, self.model) for usage in usages
            ),
        }


@dataclass
class AnalyticsMetrics:
    """Analytics 查询的过程指标。"""

    records: list[dict] = field(default_factory=list)

    def record(
        self,
        *,
        status: str,
        latency_ms: float,
        row_count: int = 0,
        cost: float = 0.0,
        permission_denied: bool = False,
        clarification: bool = False,
        repair_count: int = 0,
    ) -> None:
        self.records.append(
            {
                "status": status,
                "latency_ms": latency_ms,
                "row_count": row_count,
                "cost": cost,
                "permission_denied": permission_denied,
                "clarification": clarification,
                "repair_count": repair_count,
            }
        )

    def summary(self) -> dict[str, float]:
        count = len(self.records)
        if count == 0:
            return {
                "count": 0,
                "error_rate": 0.0,
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "avg_row_count": 0.0,
                "total_cost": 0.0,
                "permission_violation": 0,
                "clarification_rate": 0.0,
                "avg_repair_count": 0.0,
            }
        latencies = [float(record["latency_ms"]) for record in self.records]
        return {
            "count": count,
            "error_rate": sum(
                1 for record in self.records if record["status"] == "error"
            )
            / count,
            "p50_ms": float(statistics.median(latencies)),
            "p95_ms": _p95(latencies),
            "avg_row_count": sum(
                int(record["row_count"]) for record in self.records
            )
            / count,
            "total_cost": sum(
                float(record["cost"]) for record in self.records
            ),
            "permission_violation": sum(
                1
                for record in self.records
                if record["permission_denied"]
            ),
            "clarification_rate": sum(
                1
                for record in self.records
                if record["clarification"]
            )
            / count,
            "avg_repair_count": sum(
                int(record["repair_count"]) for record in self.records
            )
            / count,
        }
