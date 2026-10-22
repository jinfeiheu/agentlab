"""评测 runner:跑 golden set,输出 Markdown + JSON 报告。"""

import argparse
import json
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from config import DEEPSEEK_MODEL, DOCS_DIR, GOLDEN_PATH
from eval.data import GoldenItem, load_golden
from eval.judge import build_judge, judge_answer
from eval.retrieval_metrics import aggregate
from graph import build_graph
from metrics import MetricsRecorder, Usage, usage_from_message
from models import build_chat_model
from rag import build_inmemory_retriever, format_docs
from tools import calculator, make_search_tool, send_report

_REFUSAL_MARKERS = (
    "无法回答",
    "不知道",
    "没有找到",
    "资料不足",
    "无法从现有",
    "无法确定",
    "不能提供",
    "无法提供",
    "不能透露",
    "无法透露",
    "不便提供",
    "不会提供",
    "拒绝提供",
    "无法查询",
    "不能查询",
)


@dataclass
class EvalReport:
    """一次评测的逐题结果和汇总指标。"""

    rows: list[dict]
    generation: dict[str, float]
    retrieval: dict[str, float]


def _mean(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def _final_answer(messages: list) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            content = message.content
            if isinstance(content, str) and content.strip():
                return content.strip()
            if content:
                return str(content)
    return ""


def _tool_names(messages: list) -> set[str]:
    return {
        message.name
        for message in messages
        if isinstance(message, ToolMessage) and message.name
    }


def _sum_usage(messages: list) -> Usage | None:
    usages = [
        usage_from_message(message)
        for message in messages
        if isinstance(message, AIMessage)
    ]
    if not any(usage.total_tokens for usage in usages):
        return None
    return Usage(
        input_tokens=sum(usage.input_tokens for usage in usages),
        output_tokens=sum(usage.output_tokens for usage in usages),
        total_tokens=sum(usage.total_tokens for usage in usages),
    )


def _is_refusal(answer: str) -> bool:
    return any(marker in answer for marker in _REFUSAL_MARKERS)


def evaluate(
    graph,
    retriever,
    golden: list[GoldenItem],
    judge,
    *,
    model_name: str = "deepseek-flash",
) -> EvalReport:
    """对每条 golden 跑检索和回答,汇总指标。"""
    rows: list[dict] = []
    recorder = MetricsRecorder(model=model_name)

    for item in golden:
        # 单次预取:只用于 R@3/MRR/nDCG,代表固定检索管线的质量。
        # Agent 在 ReAct 循环里的多次检索另记在 tool_queries/evidence_labels,
        # 不混进检索指标,否则会把“检索质量”和“Agent 行为”搅在一起。
        docs = retriever.invoke(item.question)
        retrieved_ids = [
            doc.metadata.get("chunk_id", "") for doc in docs
        ]
        pre_retrieval_labels = sorted(
            set(
                re.findall(
                    r"来源:([^\]]+)\]",
                    format_docs(docs) if docs else "",
                )
            )
        )

        started = time.perf_counter()
        error = ""
        messages: list = []
        try:
            result = graph.invoke(
                {"messages": [("user", item.question)]},
                config={
                    "configurable": {
                        "thread_id": f"eval-{item.id}-{uuid.uuid4().hex}"
                    }
                },
            )
            messages = result.get("messages", [])
            if result.get("__interrupt__"):
                error = "graph interrupted"
        except Exception as exc:
            error = f"graph failed: {exc}"
        latency_ms = (time.perf_counter() - started) * 1000

        answer = _final_answer(messages)
        actual_tools = sorted(_tool_names(messages))
        usage = _sum_usage(messages)
        recorder.record("eval", latency_ms, usage)

        # judge 只看 agent 在 ReAct 循环里实际检索到的证据。
        # 预取 top-k 模型并没有看到,不能算进 citation_support。
        tool_contexts = [
            message.content
            for message in messages
            if isinstance(message, ToolMessage)
            and message.name == "search_docs"
            and isinstance(message.content, str)
        ]
        contexts = list(dict.fromkeys(tool_contexts))
        evidence_labels = sorted(
            set(re.findall(r"来源:([^\]]+)\]", "\n".join(contexts)))
        )
        tool_queries = [
            call.get("args", {}).get("query", "")
            for message in messages
            if isinstance(message, AIMessage)
            for call in message.tool_calls
            if call.get("name") == "search_docs"
        ]

        judged = judge_answer(
            judge,
            item.question,
            answer,
            contexts,
            item.key_points,
        )
        refused = (not item.answerable) and _is_refusal(answer)
        if item.answerable:
            task_success = judged.correctness >= 4 and judged.citation_support
        else:
            task_success = refused
        if error:
            task_success = False
        tool_accuracy = set(actual_tools) == set(item.expected_tools)

        rows.append(
            {
                "id": item.id,
                "question": item.question,
                "answerable": item.answerable,
                "answer": answer,
                "expected_tools": list(item.expected_tools),
                "actual_tools": actual_tools,
                "retrieved_ids": retrieved_ids,
                "relevant_ids": list(item.relevant_chunk_ids),
                "pre_retrieval_labels": pre_retrieval_labels,
                "tool_queries": tool_queries,
                "evidence_labels": evidence_labels,
                "correctness": judged.correctness,
                "faithfulness": judged.faithfulness,
                "citation_support": judged.citation_support,
                "reason": judged.reason,
                "task_success": task_success,
                "tool_accuracy": tool_accuracy,
                "refused": refused,
                "latency_ms": latency_ms,
                "usage": asdict(usage) if usage else None,
                "error": error,
            }
        )

    answerable_rows = [row for row in rows if row["answerable"]]
    unanswerable_rows = [row for row in rows if not row["answerable"]]
    summary = recorder.summary()
    generation = {
        "count": len(rows),
        "task_success": _mean([row["task_success"] for row in rows]),
        "tool_accuracy": _mean(
            [row["tool_accuracy"] for row in answerable_rows]
        ),
        "refusal_rate": _mean([row["refused"] for row in unanswerable_rows]),
        "avg_search_calls": _mean(
            [len(row["tool_queries"]) for row in answerable_rows]
        ),
        "avg_correctness": _mean([row["correctness"] for row in rows]),
        "avg_faithfulness": _mean([row["faithfulness"] for row in rows]),
        "citation_support_rate": _mean(
            [row["citation_support"] for row in answerable_rows]
        ),
        "p50_latency_ms": summary["p50_ms"],
        "p95_latency_ms": summary["p95_ms"],
        "total_tokens": summary["total_tokens"],
        "total_cost": summary["total_cost"],
    }
    retrieval = aggregate(
        [
            {
                "retrieved_ids": row["retrieved_ids"],
                "relevant_ids": set(row["relevant_ids"]),
            }
            for row in rows
            if row["answerable"]
        ],
        k=3,
    )
    return EvalReport(rows=rows, generation=generation, retrieval=retrieval)


def _format_value(value) -> str:
    return f"{value:.4f}" if isinstance(value, float) else str(value)


def write_report(report: EvalReport, path: Path) -> None:
    """写 Markdown 表格和同名 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# RAG 评测报告",
        "",
        "## 汇总",
        "",
        "### 生成",
        "",
        "| 指标 | 值 |",
        "|---|---:|",
    ]
    for key, value in report.generation.items():
        lines.append(f"| {key} | {_format_value(value)} |")
    lines += ["", "### 检索", "", "| 指标 | 值 |", "|---|---:|"]
    for key, value in report.retrieval.items():
        lines.append(f"| {key} | {_format_value(value)} |")
    lines += [
        "",
        "## 逐题结果",
        "",
        "| id | answerable | task_success | tool_accuracy | refused | "
        "correctness | faithfulness | citation_support | latency_ms | error |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in report.rows:
        lines.append(
            f"| {row['id']} | {row['answerable']} | {row['task_success']} | "
            f"{row['tool_accuracy']} | {row['refused']} | {row['correctness']} | "
            f"{row['faithfulness']} | {row['citation_support']} | "
            f"{row['latency_ms']:.1f} | {row.get('error', '')} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    json_path = path.with_suffix(".json")
    json_path.write_text(
        json.dumps(
            {
                "generation": report.generation,
                "retrieval": report.retrieval,
                "rows": report.rows,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    """命令行入口:真实评测需要 DeepSeek Key 和本地 bge-m3。"""
    parser = argparse.ArgumentParser(description="运行 RAG golden set 评测")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("eval/results/baseline.md"),
    )
    parser.add_argument(
        "--retriever",
        choices=["baseline", "hybrid"],
        default="baseline",
    )
    parser.add_argument("--rerank", action="store_true")
    args = parser.parse_args()

    if not os.getenv("DEEPSEEK_API_KEY"):
        raise SystemExit(
            "缺少 DEEPSEEK_API_KEY:请复制 .env.example 为 .env 并填入你的 DeepSeek Key。"
        )
    if args.retriever != "baseline":
        raise SystemExit("hybrid 检索在 Task 10 接入。")
    if args.rerank:
        raise SystemExit("rerank 在 Task 11 接入。")

    golden = load_golden(GOLDEN_PATH)
    if args.limit:
        golden = golden[: args.limit]

    retriever = build_inmemory_retriever(DOCS_DIR)
    tools = [calculator, make_search_tool(retriever), send_report]
    graph = build_graph(
        build_chat_model(),
        tools,
        checkpointer=InMemorySaver(),
    )
    judge = build_judge()
    report = evaluate(
        graph,
        retriever,
        golden,
        judge,
        model_name=DEEPSEEK_MODEL,
    )
    write_report(report, args.output)
    print(f"已写入 {args.output} 和 {args.output.with_suffix('.json')}")
    print(
        json.dumps(
            {
                "generation": report.generation,
                "retrieval": report.retrieval,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
