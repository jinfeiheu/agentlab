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


def test_tracing_disabled_is_noop():
    provider = setup_tracing(exporter=None)
    with span("noop"):
        pass
    assert provider is not None
