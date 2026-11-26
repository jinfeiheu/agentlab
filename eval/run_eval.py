"""评测 runner:跑 golden set,输出 Markdown + JSON 报告。"""

import argparse
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from agentlab.config import (
    DEEPSEEK_MODEL,
    DOCS_DIR,
    EVAL_JUDGE_MODEL,
    GOLDEN_PATH,
    HARD_DOCS_DIR,
    HARD_GOLDEN_PATH,
    PG_COLLECTION,
    PG_HARD_COLLECTION,
    RERANK_DEVICE,
    RERANK_MODEL,
)
from eval.data import GoldenItem, load_golden
from eval.judge import build_judge, judge_answer
from eval.retrieval_metrics import (
    aggregate,
    citation_precision,
    context_precision,
    context_recall,
)
from eval.text_metrics import exact_match, token_f1
from agentlab.rag_agent.graph import build_graph
from agentlab.observability.metrics import MetricsRecorder, Usage, usage_from_message
from agentlab.models import build_chat_model
from agentlab.rag_agent.rag.loaders import build_inmemory_retriever, format_docs
from agentlab.rag_agent.rag.retrieval import (
    build_pgvector_hybrid_retriever,
    build_reranker,
    extract_sources,
)
from agentlab.rag_agent.tools.builtin import calculator, make_search_tool, send_report

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

_DIFFICULTY_ORDER = ("easy", "medium", "hard")
_STRATUM_METRICS = (
    "count",
    "task_success",
    "answerable_success",
    "avg_correctness",
    "avg_faithfulness",
    "citation_support_rate",
    "refusal_rate",
    "avg_token_f1",
    "exact_match",
    "context_precision",
    "context_recall",
    "citation_precision",
    "tool_accuracy",
    "avg_search_calls",
    "p50_latency_ms",
    "p95_latency_ms",
    "total_tokens",
    "total_cost",
)


@dataclass
class EvalReport:
    """一次评测的逐题结果、汇总指标和分层结果。"""

    rows: list[dict]
    generation: dict[str, float]
    retrieval: dict[str, float]
    strata: dict[str, dict[str, dict]] = field(default_factory=dict)
    closed_book: bool = False
    judge_model: str = ""
    corpus: str = ""


def _mean(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def _mean_or_none(values: list) -> float | None:
    """没有可适用样本时返回 None,报告里显示为 n/a。"""
    return sum(values) / len(values) if values else None


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


def _row_usage(row: dict) -> Usage | None:
    usage = row.get("usage")
    return Usage(**usage) if usage else None


def _group_metrics(rows: list[dict], model_name: str) -> dict[str, float]:
    """对一组 row 计算生成/上下文指标;用于总体与分层报告。"""
    recorder = MetricsRecorder(model=model_name)
    for row in rows:
        recorder.record("eval", row["latency_ms"], _row_usage(row))
    summary = recorder.summary()

    answerable = [row for row in rows if row["answerable"]]
    unanswerable = [row for row in rows if not row["answerable"]]
    with_reference = [row for row in rows if row["token_f1"] is not None]
    return {
        "count": len(rows),
        "task_success": _mean([row["task_success"] for row in rows]),
        "answerable_success": _mean_or_none(
            [
                row["answerable_success"]
                for row in answerable
                if row["answerable_success"] is not None
            ]
        ),
        "tool_accuracy": _mean_or_none(
            [row["tool_accuracy"] for row in answerable]
        ),
        "refusal_rate": _mean_or_none(
            [row["refused"] for row in unanswerable]
        ),
        "avg_search_calls": _mean_or_none(
            [len(row["tool_queries"]) for row in answerable]
        ),
        "avg_correctness": _mean([row["correctness"] for row in rows]),
        "avg_faithfulness": _mean([row["faithfulness"] for row in rows]),
        "citation_support_rate": _mean_or_none(
            [row["citation_support"] for row in answerable]
        ),
        "avg_token_f1": _mean_or_none(
            [row["token_f1"] for row in with_reference]
        ),
        "exact_match": _mean_or_none(
            [row["exact_match"] for row in with_reference]
        ),
        "context_precision": _mean_or_none(
            [
                row["context_precision"]
                for row in answerable
                if row["context_precision"] is not None
            ]
        ),
        "context_recall": _mean_or_none(
            [
                row["context_recall"]
                for row in answerable
                if row["context_recall"] is not None
            ]
        ),
        "citation_precision": _mean_or_none(
            [row["citation_precision"] for row in answerable]
        ),
        "p50_latency_ms": summary["p50_ms"],
        "p95_latency_ms": summary["p95_ms"],
        "total_tokens": summary["total_tokens"],
        "total_cost": summary["total_cost"],
    }


def _strata(rows: list[dict], model_name: str) -> dict[str, dict]:
    """按 difficulty 和 category 分组汇总。"""
    result: dict[str, dict] = {}
    for dimension in ("difficulty", "category"):
        groups: dict[str, list[dict]] = {}
        for row in rows:
            groups.setdefault(row[dimension], []).append(row)
        if dimension == "difficulty":
            ordered = [
                key for key in _DIFFICULTY_ORDER if key in groups
            ] + sorted(key for key in groups if key not in _DIFFICULTY_ORDER)
        else:
            ordered = sorted(groups)
        result[dimension] = {
            key: _group_metrics(groups[key], model_name)
            for key in ordered
        }
    return result


def evaluate(
    graph,
    retriever,
    golden: list[GoldenItem],
    judge,
    *,
    model_name: str = "deepseek-flash",
    closed_book: bool = False,
    judge_model: str | None = None,
    corpus: str = "",
) -> EvalReport:
    """对每条 golden 跑检索和回答,汇总指标。"""
    rows: list[dict] = []

    for item in golden:
        # 单次预取:只用于 Recall/MRR/nDCG/context precision,
        # 代表固定检索管线的质量;closed-book 消融时不检索。
        if closed_book:
            docs = []
            retrieved_ids: list[str] = []
            pre_retrieval_labels: list[str] = []
        else:
            docs = retriever.invoke(item.question)
            retrieved_ids = [
                doc.metadata.get("chunk_id", "") for doc in docs
            ]
            pre_retrieval_labels = sorted(
                set(extract_sources(format_docs(docs) if docs else ""))
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
        evidence_labels = sorted(set(extract_sources("\n".join(contexts))))
        tool_queries = [
            call.get("args", {}).get("query", "")
            for message in messages
            if isinstance(message, AIMessage)
            for call in message.tool_calls
            if call.get("name") == "search_docs"
        ]
        citations = sorted(set(extract_sources(answer)))

        judged = judge_answer(
            judge,
            item.question,
            answer,
            contexts,
            item.key_points,
            item.reference_answer,
        )
        refused = (not item.answerable) and _is_refusal(answer)
        answerable_success = (
            judged.correctness >= 4 if item.answerable else None
        )
        if item.answerable:
            if closed_book:
                # 闭卷没有可引用的工具证据,citation_support 不适用。
                task_success = answerable_success
            else:
                task_success = (
                    answerable_success and judged.citation_support
                )
        else:
            # 拒答还不够:如果拒答后继续编造,faithfulness 会变低。
            task_success = refused and judged.faithfulness >= 4
        if error:
            task_success = False
            answerable_success = False if item.answerable else None
        # 允许安全的额外工具(例如算术题同时查资料和用计算器);
        # 只有缺失必需工具才算工具选择失败。
        tool_accuracy = set(item.expected_tools).issubset(set(actual_tools))

        rows.append(
            {
                "id": item.id,
                "question": item.question,
                "answerable": item.answerable,
                "difficulty": item.difficulty,
                "category": item.category,
                "reference_answer": item.reference_answer,
                "answer": answer,
                "expected_tools": list(item.expected_tools),
                "actual_tools": actual_tools,
                "retrieved_ids": retrieved_ids,
                "relevant_ids": list(item.relevant_chunk_ids),
                "pre_retrieval_labels": pre_retrieval_labels,
                "tool_queries": tool_queries,
                "evidence_labels": evidence_labels,
                "citations": citations,
                "correctness": judged.correctness,
                "faithfulness": judged.faithfulness,
                "citation_support": judged.citation_support,
                "reason": judged.reason,
                "task_success": task_success,
                "answerable_success": answerable_success,
                "tool_accuracy": tool_accuracy,
                "refused": refused,
                "token_f1": (
                    token_f1(answer, item.reference_answer)
                    if item.reference_answer
                    else None
                ),
                "exact_match": (
                    exact_match(answer, item.reference_answer)
                    if item.reference_answer
                    else None
                ),
                "context_precision": (
                    context_precision(
                        retrieved_ids, set(item.relevant_chunk_ids), 3
                    )
                    if item.answerable and not closed_book
                    else None
                ),
                "context_recall": (
                    context_recall(
                        retrieved_ids, set(item.relevant_chunk_ids), 3
                    )
                    if item.answerable and not closed_book
                    else None
                ),
                "citation_precision": citation_precision(
                    citations, set(evidence_labels)
                ),
                "latency_ms": latency_ms,
                "usage": asdict(usage) if usage else None,
                "error": error,
            }
        )

    answerable_rows = [row for row in rows if row["answerable"]]
    generation = _group_metrics(rows, model_name)
    retrieval: dict[str, float] = {}
    if not closed_book:
        retrieval = aggregate(
            [
                {
                    "retrieved_ids": row["retrieved_ids"],
                    "relevant_ids": set(row["relevant_ids"]),
                }
                for row in answerable_rows
            ],
            k=3,
        )
        retrieval["context_precision"] = _mean(
            [row["context_precision"] for row in answerable_rows]
        )
        retrieval["context_recall"] = _mean(
            [row["context_recall"] for row in answerable_rows]
        )
    return EvalReport(
        rows=rows,
        generation=generation,
        retrieval=retrieval,
        strata=_strata(rows, model_name),
        closed_book=closed_book,
        judge_model=judge_model or "",
        corpus=corpus,
    )


def _format_value(value) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}" if isinstance(value, float) else str(value)


def _format_strata(report: EvalReport) -> list[str]:
    lines = ["", "## 分层结果", ""]
    for dimension, groups in report.strata.items():
        if not groups:
            continue
        lines += [f"### 按 {dimension}", ""]
        header = "| 指标 | " + " | ".join(groups) + " |"
        lines += [header, "|---|" + "---:|" * len(groups)]
        for metric in _STRATUM_METRICS:
            values = [
                _format_value(groups[group].get(metric, ""))
                for group in groups
            ]
            lines.append(
                f"| {metric} | " + " | ".join(values) + " |"
            )
        lines.append("")
    return lines


def write_report(report: EvalReport, path: Path) -> None:
    """写 Markdown 表格和同名 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# RAG 评测报告",
        "",
        "## 配置",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| corpus | {report.corpus or 'unspecified'} |",
        f"| judge_model | {report.judge_model or 'unspecified'} |",
        f"| closed_book | {report.closed_book} |",
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
    lines += _format_strata(report)
    lines += [
        "## 逐题结果",
        "",
        "| id | difficulty | category | answerable | task_success | "
        "tool_accuracy | refused | correctness | faithfulness | "
        "citation_support | token_f1 | citation_precision | latency_ms | "
        "error |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in report.rows:
        token_f1_value = (
            "" if row["token_f1"] is None else f"{row['token_f1']:.4f}"
        )
        lines.append(
            f"| {row['id']} | {row['difficulty']} | {row['category']} | "
            f"{row['answerable']} | {row['task_success']} | "
            f"{row['tool_accuracy']} | {row['refused']} | "
            f"{row['correctness']} | {row['faithfulness']} | "
            f"{row['citation_support']} | {token_f1_value} | "
            f"{row['citation_precision']:.4f} | {row['latency_ms']:.1f} | "
            f"{row.get('error', '')} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    json_path = path.with_suffix(".json")
    json_path.write_text(
        json.dumps(
            {
                "generation": report.generation,
                "retrieval": report.retrieval,
                "strata": report.strata,
                "corpus": report.corpus,
                "judge_model": report.judge_model,
                "closed_book": report.closed_book,
                "rows": report.rows,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )


def _build_retriever(args, docs_dir, collection_name):
    if args.retriever == "hybrid":
        return build_pgvector_hybrid_retriever(
            docs_dir=docs_dir, collection_name=collection_name
        )
    return build_inmemory_retriever(docs_dir)


def main() -> None:
    """命令行入口:真实评测需要 DeepSeek Key 和本地 bge-m3。"""
    parser = argparse.ArgumentParser(description="运行 RAG golden set 评测")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--corpus",
        choices=["easy", "hard"],
        default="easy",
        help="easy=冻结回归集,hard=加固评测集",
    )
    parser.add_argument(
        "--golden",
        type=Path,
        default=None,
        help="自定义 golden JSONL;默认按 corpus 选择",
    )
    parser.add_argument(
        "--retriever",
        choices=["baseline", "hybrid"],
        default="baseline",
    )
    parser.add_argument(
        "--rerank",
        action="store_true",
        help="启用专用 cross-encoder rerank",
    )
    parser.add_argument(
        "--llm-rerank",
        action="store_true",
        help="叠加 LLM rerank",
    )
    parser.add_argument(
        "--closed-book",
        action="store_true",
        help="不提供 search_docs,做检索贡献消融",
    )
    parser.add_argument(
        "--judge-model",
        default=None,
        help="裁判模型名;默认 EVAL_JUDGE_MODEL,可传 qwen3:8b 走 Ollama",
    )
    args = parser.parse_args()

    if not os.getenv("DEEPSEEK_API_KEY"):
        raise SystemExit(
            "缺少 DEEPSEEK_API_KEY:请复制 .env.example 为 .env 并填入你的 DeepSeek Key。"
        )
    hard = args.corpus == "hard"
    docs_dir = HARD_DOCS_DIR if hard else DOCS_DIR
    collection_name = PG_HARD_COLLECTION if hard else PG_COLLECTION
    golden_path = args.golden or (HARD_GOLDEN_PATH if hard else GOLDEN_PATH)
    output_path = args.output or Path(
        f"eval/results/{'hard-' if hard else ''}baseline.md"
    )

    golden = load_golden(golden_path)
    if args.limit:
        golden = golden[: args.limit]

    retriever = _build_retriever(args, docs_dir, collection_name)
    reranker = build_reranker(
        use_model=args.rerank,
        use_llm=args.llm_rerank,
        model_name=RERANK_MODEL,
        device=RERANK_DEVICE,
    )
    if args.closed_book:
        tools = []
    else:
        tools = [
            calculator,
            make_search_tool(retriever, reranker=reranker),
            send_report,
        ]
    graph = build_graph(
        build_chat_model(),
        tools,
        checkpointer=InMemorySaver(),
    )
    judge_model = args.judge_model or EVAL_JUDGE_MODEL
    print(
        f"评测:corpus={args.corpus}, retriever={args.retriever}, "
        f"rerank_model={args.rerank}, llm_rerank={args.llm_rerank}, "
        f"closed_book={args.closed_book}, judge={judge_model}"
    )
    judge = build_judge(judge_model)
    report = evaluate(
        graph,
        retriever,
        golden,
        judge,
        model_name=DEEPSEEK_MODEL,
        closed_book=args.closed_book,
        judge_model=judge_model,
        corpus=args.corpus,
    )
    write_report(report, output_path)
    print(
        f"已写入 {output_path} 和 {output_path.with_suffix('.json')}"
    )
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
