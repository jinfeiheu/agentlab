import json

from langchain_core.runnables import RunnableLambda
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from tracing import setup_tracing, span


def test_span_records_attributes():
    exporter = InMemorySpanExporter()
    provider = setup_tracing(exporter=exporter)
    with span("retrieve", query="hello"):
        pass
    spans = exporter.get_finished_spans()
    assert spans[0].name == "retrieve"
    assert spans[0].attributes["query"] == "hello"


def test_span_redacts_pii_attributes():
    exporter = InMemorySpanExporter()
    setup_tracing(exporter=exporter)
    with span("retrieve", query="联系 alice@example.com 或 13800138000"):
        pass
    spans = exporter.get_finished_spans()
    query = spans[0].attributes["query"]
    assert "alice@example.com" not in query
    assert "13800138000" not in query
    assert "[EMAIL]" in query and "[PHONE]" in query


def test_auto_instrumented_spans_redact_pii():
    exporter = InMemorySpanExporter()
    setup_tracing(exporter=exporter)
    RunnableLambda(lambda value: f"联系 {value}").invoke(
        "alice@example.com 13800138000"
    )
    spans = exporter.get_finished_spans()
    assert spans
    dumped = json.dumps(
        [
            {
                "attributes": dict(span.attributes or {}),
                "events": [
                    dict(getattr(event, "attributes", {}) or {})
                    for event in getattr(span, "events", ())
                ],
            }
            for span in spans
        ],
        default=str,
        ensure_ascii=False,
    )
    assert "alice@example.com" not in dumped
    assert "13800138000" not in dumped
    assert "[EMAIL]" in dumped


def test_span_event_attributes_are_redacted():
    exporter = InMemorySpanExporter()
    setup_tracing(exporter=exporter)
    with span("event") as current_span:
        current_span.add_event(
            "note", {"text": "联系 alice@example.com"}
        )
    event = exporter.get_finished_spans()[0].events[0]
    assert "alice@example.com" not in str(dict(event.attributes))


def test_tracing_disabled_is_noop():
    provider = setup_tracing(exporter=None)
    with span("noop"):
        pass
    assert provider is not None
