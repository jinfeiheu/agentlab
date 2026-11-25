"""Analytics 并发压测：记录 P50/P95/P99、错误率与单任务成本。

示例：
  uv run python scripts/load_analytics.py --concurrency 20 --total 20 \
    --auto-approve --output eval/results/analytics-load-20.json
"""

import argparse
import asyncio
import json
import time
from pathlib import Path

from eval.run_analytics_eval import (
    TokenUsageTracker,
    _percentile,
    actual_outcome,
    estimate_cost,
    load_golden,
)
from agentlab.analytics import graph as graph_module
from agentlab.analytics.db import AnalyticsDB
from agentlab.analytics.graph import (
    build_analytics_graph,
    run_analytics_question,
)
from agentlab.analytics.versioning import build_model_router
from agentlab.config import ANALYTICS_GOLDEN_PATH, REQUEST_TIMEOUT
from agentlab.models import build_chat_model


async def _one(
    graph,
    item: dict,
    index: int,
    timeout: float,
    price: float,
) -> dict:
    started = time.perf_counter()
    tracker = TokenUsageTracker()
    try:
        state = await asyncio.wait_for(
            run_analytics_question(
                graph,
                item["question"],
                item["tenant_id"],
                user_id=f"load-{index}",
                config={"callbacks": [tracker]},
            ),
            timeout=timeout,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        outcome = actual_outcome(state)
        result = state.get("result") or {}
        success = outcome == "answer" and bool(result.get("columns"))
        tokens = tracker.total_tokens
        cost = (
            tokens / 1000 * price
            if tokens
            else estimate_cost(
                item["question"],
                state.get("sql", ""),
                state.get("answer", ""),
                price,
            )
        )
        return {
            "question": item["question"],
            "outcome": outcome,
            "success": success,
            "latency_ms": latency_ms,
            "tokens": tokens,
            "cost_estimate": cost,
            "error": state.get("sql_error", ""),
        }
    except asyncio.TimeoutError:
        return {
            "question": item["question"],
            "outcome": "timeout",
            "success": False,
            "latency_ms": (time.perf_counter() - started) * 1000,
            "cost_estimate": 0.0,
            "error": "client timeout",
        }
    except Exception as exc:  # noqa: BLE001 - 压测不中断
        return {
            "question": item["question"],
            "outcome": "error",
            "success": False,
            "latency_ms": (time.perf_counter() - started) * 1000,
            "cost_estimate": 0.0,
            "error": str(exc),
        }


async def run_load(
    concurrency: int,
    total: int,
    timeout: float,
    price: float,
    auto_approve: bool,
) -> dict:
    items = [
        item
        for item in load_golden(Path(ANALYTICS_GOLDEN_PATH))
        if item.get("expected_outcome") == "answer"
    ]
    if not items:
        raise SystemExit("golden 中没有可回答题")
    if auto_approve:
        graph_module.COST_THRESHOLD = float("inf")
    graph = build_analytics_graph(
        build_chat_model(temperature=0),
        AnalyticsDB(),
        model_router=build_model_router(temperature=0),
    )
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def guarded(index: int) -> dict:
        async with semaphore:
            return await _one(
                graph,
                items[index % len(items)],
                index,
                timeout,
                price,
            )

    started = time.perf_counter()
    records = await asyncio.gather(
        *(guarded(index) for index in range(total))
    )
    wall_ms = (time.perf_counter() - started) * 1000
    latencies = sorted(record["latency_ms"] for record in records)
    failures = [record for record in records if not record["success"]]
    return {
        "concurrency": concurrency,
        "total": total,
        "wall_ms": wall_ms,
        "success_rate": 1 - len(failures) / len(records),
        "error_rate": len(failures) / len(records),
        "p50_ms": _percentile(latencies, 50),
        "p95_ms": _percentile(latencies, 95),
        "p99_ms": _percentile(latencies, 99),
        "avg_cost_estimate": (
            sum(record["cost_estimate"] for record in records)
            / len(records)
        ),
        "total_cost_estimate": sum(
            record["cost_estimate"] for record in records
        ),
        "failures": failures[:20],
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analytics 并发压测")
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--total", type=int, default=None)
    parser.add_argument(
        "--timeout", type=float, default=REQUEST_TIMEOUT + 5
    )
    parser.add_argument("--price-per-1k", type=float, default=0.002)
    parser.add_argument("--auto-approve", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    total = args.total if args.total is not None else args.concurrency
    report = asyncio.run(
        run_load(
            args.concurrency,
            total,
            args.timeout,
            args.price_per_1k,
            args.auto_approve,
        )
    )
    summary = {
        key: value
        for key, value in report.items()
        if key not in {"records", "failures"}
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"报告已写入 {args.output}")


if __name__ == "__main__":
    main()
