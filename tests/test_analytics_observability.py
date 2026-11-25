"""Analytics 可观测测试：指标、日志和 span。"""

import logging

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from agentlab.analytics import graph as graph_module
from agentlab.analytics.db import QueryResult
from agentlab.analytics.graph import (
    AnswerOutput,
    Intent,
    SQLPlan,
    build_analytics_graph,
    run_analytics_question,
)
from agentlab.observability.metrics import AnalyticsMetrics
from agentlab.observability.tracing import setup_tracing


class _Model:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def with_structured_output(self, schema, **kwargs):
        return self

    async def ainvoke(self, prompt, **kwargs):
        result = self.results[self.calls]
        self.calls += 1
        return result


class _DB:
    async def explain(self, sql_text, tenant_id, timeout_ms=5000):
        return 0.0

    async def execute(
        self, sql_text, tenant_id, max_rows=200, timeout_ms=5000
    ):
        return QueryResult(
            columns=["x"],
            rows=[[1]],
            row_count=1,
            truncated=False,
            duration_ms=1.0,
        )


@pytest.fixture(autouse=True)
def _stub_audit(monkeypatch):
    async def noop(**kwargs):
        return None

    monkeypatch.setattr(
        graph_module, "write_audit", noop, raising=False
    )


def test_analytics_metrics_summary():
    metrics = AnalyticsMetrics()
    metrics.record(
        status="success", latency_ms=10, row_count=5, cost=0.01
    )
    metrics.record(status="error", latency_ms=20)
    metrics.record(
        status="clarify", latency_ms=30, clarification=True
    )
    metrics.record(
        status="rejected", latency_ms=40, permission_denied=True
    )

    summary = metrics.summary()

    assert summary["count"] == 4
    assert summary["error_rate"] == 0.25
    assert summary["p50_ms"] == 25.0
    assert summary["p95_ms"] == 40.0
    assert summary["avg_row_count"] == 1.25
    assert summary["total_cost"] == 0.01
    assert summary["permission_violation"] == 1
    assert summary["clarification_rate"] == 0.25
    assert summary["avg_repair_count"] == 0.0


async def test_query_log_has_no_pii(caplog):
    caplog.set_level(logging.INFO)
    model = _Model(
        [
            Intent(intent="answer"),
            SQLPlan(sql="SELECT * FROM orders"),
            AnswerOutput(answer="查询成功"),
        ]
    )
    graph = build_analytics_graph(model, _DB())

    await run_analytics_question(
        graph, "alice@example.com 的订单", "tenant_a"
    )

    assert "analytics_query" in caplog.text
    assert "status=success" in caplog.text
    assert "request_id=" in caplog.text
    assert "alice@example.com" not in caplog.text


async def test_analytics_spans_emitted():
    exporter = InMemorySpanExporter()
    setup_tracing(exporter=exporter)
    model = _Model(
        [
            Intent(intent="answer"),
            SQLPlan(sql="SELECT * FROM orders"),
            AnswerOutput(answer="查询成功"),
        ]
    )
    graph = build_analytics_graph(model, _DB())

    await run_analytics_question(graph, "上个月收入", "tenant_a")

    spans = exporter.get_finished_spans()
    names = {span.name for span in spans}
    assert {
        "analytics.understand",
        "analytics.plan_sql",
        "analytics.validate_sql",
        "analytics.estimate_cost",
        "analytics.approve",
        "analytics.execute",
        "analytics.answer",
        "analytics.model",
    } <= names
    model_spans = [span for span in spans if span.name == "analytics.model"]
    assert model_spans
    assert model_spans[0].attributes["prompt_version"] == "v1"
    assert model_spans[0].attributes["model_id"] == "default"
