"""Analytics golden 评测：execution accuracy、澄清/拒答率、延迟与成本。"""

import argparse
import asyncio
import json
import math
import os
import time
from decimal import Decimal
from pathlib import Path

import tiktoken

from agentlab.analytics.db import AnalyticsDB
from agentlab.analytics.graph import (
    build_analytics_graph,
    run_analytics_question,
)
from agentlab.config import ANALYTICS_GOLDEN_PATH
from agentlab.models import build_chat_model

REFUSAL_MARKERS = (
    "无法回答",
    "无法查询",
    "不能提供",
    "无法提供",
    "没有相关数据",
    "数据中没有",
)

_ENCODING = None


def load_golden(path: Path) -> list[dict]:
    """逐行读取 golden JSONL，忽略空行。"""
    items: list[dict] = []
    with Path(path).open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def _normalize_value(value):
    """统一数值精度、字符串空白和空值，避免格式差异造成误判。"""
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        return round(float(value), 2)
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _canonical(rows) -> list[tuple]:
    normalized = [
        tuple(_normalize_value(value) for value in row)
        for row in (rows or [])
    ]
    return sorted(
        normalized,
        key=lambda row: json.dumps(row, ensure_ascii=False, default=str),
    )


def _align_rows(columns, rows, expected_columns):
    """列名可匹配时按期望列顺序重排；否则保持原顺序。"""
    aligned = [tuple(row) for row in (rows or [])]
    if not expected_columns:
        return aligned
    actual = [str(column).strip().lower() for column in (columns or [])]
    expected = [str(column).strip().lower() for column in expected_columns]
    if not set(expected).issubset(set(actual)):
        return aligned
    indices = [actual.index(name) for name in expected]
    return [tuple(row[index] for index in indices) for row in aligned]


def rows_match(
    actual_columns,
    actual_rows,
    expected_columns,
    expected_rows,
) -> bool:
    """顺序不敏感、数值容差 0.01、支持空值的结果比较。"""
    aligned = _align_rows(actual_columns, actual_rows, expected_columns)
    return _canonical(aligned) == _canonical(expected_rows)


def actual_outcome(state: dict) -> str:
    """从图状态推断 answer/clarify/refuse/error。"""
    if state.get("clarification"):
        return "clarify"
    answer = state.get("answer") or ""
    if any(marker in answer for marker in REFUSAL_MARKERS):
        return "refuse"
    result = state.get("result") or {}
    if "columns" in result:
        return "answer"
    return "error"


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    index = max(0, math.ceil(percentile / 100 * len(values)) - 1)
    return values[index]


def compute_metrics(records: list[dict]) -> dict:
    """汇总 outcome 指标、过程指标、延迟和成本。"""
    answer = [
        record
        for record in records
        if record.get("expected_outcome") == "answer"
    ]
    clarify = [
        record
        for record in records
        if record.get("expected_outcome") == "clarify"
    ]
    refuse = [
        record
        for record in records
        if record.get("expected_outcome") == "refuse"
    ]
    latencies = sorted(float(record.get("latency_ms", 0)) for record in records)
    costs = [float(record.get("cost_estimate", 0)) for record in records]
    return {
        "count": len(records),
        "task_success": _mean(
            [1.0 if record.get("matched") else 0.0 for record in records]
        ),
        "execution_accuracy": _mean(
            [1.0 if record.get("matched") else 0.0 for record in answer]
        ),
        "clarification_rate": _mean(
            [1.0 if record.get("matched") else 0.0 for record in clarify]
        ),
        "refusal_rate": _mean(
            [1.0 if record.get("matched") else 0.0 for record in refuse]
        ),
        "permission_violation": sum(
            1 for record in records if record.get("permission_violation")
        ),
        "avg_repair_count": _mean(
            [float(record.get("repair_count", 0)) for record in records]
        ),
        "p50_latency_ms": _percentile(latencies, 50),
        "p95_latency_ms": _percentile(latencies, 95),
        "total_cost_estimate": sum(costs),
        "avg_cost_estimate": _mean(costs),
    }


def _token_count(text: str) -> int:
    global _ENCODING
    if not text:
        return 0
    try:
        if _ENCODING is None:
            _ENCODING = tiktoken.get_encoding("cl100k_base")
        return len(_ENCODING.encode(text))
    except Exception:  # noqa: BLE001 - 估算失败时退化为字符数
        return max(1, len(text) // 4)


def estimate_cost(
    question: str, sql: str, answer: str, price_per_1k: float
) -> float:
    """按输入/输出 token 估算成本；不是账单级精确值。"""
    tokens = (
        _token_count(question) + _token_count(sql) + _token_count(answer)
    )
    return tokens / 1000 * price_per_1k


def _matches(item: dict, state: dict, outcome: str) -> bool:
    expected = item.get("expected_outcome")
    if expected != "answer":
        return outcome == expected
    if outcome != "answer":
        return False
    result = state.get("result") or {}
    return rows_match(
        result.get("columns") or [],
        result.get("rows") or [],
        item.get("expected_columns"),
        item.get("expected_result") or [],
    )


async def run_eval(
    items: list[dict], graph, cost_per_1k: float | None = None
) -> dict:
    """逐题执行并返回 summary + records；graph 可注入 fake。"""
    price = (
        cost_per_1k
        if cost_per_1k is not None
        else float(os.getenv("ANALYTICS_EVAL_COST_PER_1K", "0.002"))
    )
    records = []
    for item in items:
        started = time.perf_counter()
        try:
            state = await run_analytics_question(
                graph, item["question"], item["tenant_id"]
            )
            latency_ms = (time.perf_counter() - started) * 1000
            outcome = actual_outcome(state)
            record = {
                "question": item["question"],
                "tenant_id": item["tenant_id"],
                "expected_outcome": item.get("expected_outcome"),
                "actual_outcome": outcome,
                "matched": _matches(item, state, outcome),
                "latency_ms": latency_ms,
                "cost_estimate": estimate_cost(
                    item["question"],
                    state.get("sql", ""),
                    state.get("answer", ""),
                    price,
                ),
                "repair_count": state.get("repair_count", 0),
                "sql": state.get("sql", ""),
                "answer": state.get("answer", ""),
                "result": state.get("result") or {},
                "error": state.get("sql_error", ""),
                "tags": item.get("tags", []),
            }
        except Exception as exc:  # noqa: BLE001 - 单题失败不中断评测
            record = {
                "question": item["question"],
                "tenant_id": item["tenant_id"],
                "expected_outcome": item.get("expected_outcome"),
                "actual_outcome": "error",
                "matched": False,
                "latency_ms": (time.perf_counter() - started) * 1000,
                "cost_estimate": 0.0,
                "repair_count": 0,
                "sql": "",
                "answer": "",
                "result": {},
                "error": str(exc),
                "tags": item.get("tags", []),
            }
        records.append(record)
    return {"summary": compute_metrics(records), "records": records}


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 analytics golden 评测")
    parser.add_argument(
        "--golden",
        type=Path,
        default=ANALYTICS_GOLDEN_PATH,
        help="golden JSONL 路径",
    )
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 条")
    parser.add_argument(
        "--output", type=Path, default=None, help="完整 JSON 报告输出路径"
    )
    args = parser.parse_args()

    items = load_golden(args.golden)
    if args.limit is not None:
        items = items[: args.limit]
    graph = build_analytics_graph(
        build_chat_model(temperature=0), AnalyticsDB()
    )
    report = asyncio.run(run_eval(items, graph))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    for record in report["records"]:
        if not record["matched"]:
            print(
                f"BAD: {record['question']} "
                f"expected={record['expected_outcome']} "
                f"actual={record['actual_outcome']} "
                f"error={record.get('error', '')}"
            )
    if args.output:
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"报告已写入 {args.output}")


if __name__ == "__main__":
    main()
