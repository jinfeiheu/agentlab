"""OpenTelemetry / Phoenix 追踪初始化与手动 span。"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from openinference.instrumentation.langchain import LangChainInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
)

from config import PHOENIX_ENDPOINT, TRACING_ENABLED
from security import redact_pii

_provider: TracerProvider | None = None
_instrumentor: LangChainInstrumentor | None = None
_global_provider_set = False


def _redact_otel_value(value):
    """递归脱敏 OTel 属性值;数字/布尔等非字符串原样保留。"""
    if isinstance(value, str):
        return redact_pii(value)
    if isinstance(value, dict):
        return {
            key: _redact_otel_value(item) for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact_otel_value(item) for item in value]
    return value


def _redact_span(span) -> None:
    """就地脱敏一个 ReadableSpan 的属性与事件属性。

    ReadableSpan 的 _attributes 是不可变的 BoundedAttributes,所以整体
    替换成普通 dict;span.attributes 仍会返回同样的键值。
    """
    attributes = getattr(span, "_attributes", None)
    if attributes is not None:
        span._attributes = {
            key: _redact_otel_value(value)
            for key, value in attributes.items()
        }
    for event in getattr(span, "_events", ()) or ():
        event_attributes = getattr(event, "_attributes", None)
        if event_attributes is not None:
            event._attributes = {
                key: _redact_otel_value(value)
                for key, value in event_attributes.items()
            }


class RedactingSpanExporter(SpanExporter):
    """在导出前统一脱敏;覆盖 OpenInference 自动产生的输入/输出属性。"""

    def __init__(self, delegate: SpanExporter):
        self._delegate = delegate

    def export(self, spans):
        for span in spans:
            _redact_span(span)
        return self._delegate.export(spans)

    def shutdown(self) -> None:
        self._delegate.shutdown()

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        return self._delegate.force_flush(timeout_millis)


def setup_tracing(exporter: SpanExporter | None = None) -> TracerProvider:
    """初始化 TracerProvider;测试可传入内存 exporter,否则按配置导出到 Phoenix。"""
    global _provider, _instrumentor, _global_provider_set
    _shutdown_current()

    provider = TracerProvider()
    if exporter is not None:
        provider.add_span_processor(
            SimpleSpanProcessor(RedactingSpanExporter(exporter))
        )
    elif TRACING_ENABLED:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        provider.add_span_processor(
            BatchSpanProcessor(
                RedactingSpanExporter(
                    OTLPSpanExporter(endpoint=PHOENIX_ENDPOINT)
                )
            )
        )

    # 全局 provider 只能设置一次;重复 setup 时手动 span 仍使用最新的 provider。
    if not _global_provider_set:
        trace.set_tracer_provider(provider)
        _global_provider_set = True
    _provider = provider

    instrumentor = LangChainInstrumentor()
    if instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.uninstrument()
    instrumentor.instrument(tracer_provider=provider)
    _instrumentor = instrumentor
    return provider


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[trace.Span]:
    """创建手动 span;属性值统一转成字符串,并脱敏 PII。"""
    tracer = (
        _provider.get_tracer(__name__)
        if _provider is not None
        else trace.get_tracer(__name__)
    )
    with tracer.start_as_current_span(name) as current_span:
        for key, value in attributes.items():
            current_span.set_attribute(key, redact_pii(str(value)))
        yield current_span


def shutdown_tracing() -> None:
    """关闭 provider,确保 BatchSpanProcessor 中尚未导出的 span 被刷出。"""
    _shutdown_current()


def _shutdown_current() -> None:
    """清理上一次 setup 创建的 provider 和 instrumentor。"""
    global _provider, _instrumentor
    if _instrumentor is not None:
        if _instrumentor.is_instrumented_by_opentelemetry:
            _instrumentor.uninstrument()
        _instrumentor = None
    if _provider is not None:
        _provider.shutdown()
        _provider = None
