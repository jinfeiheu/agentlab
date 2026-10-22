import pytest
from langchain_core.messages import AIMessage

from metrics import MetricsRecorder, Usage, estimate_cost, usage_from_message


def test_usage_and_cost():
    usage = Usage(1000, 500, 1500)
    assert (
        estimate_cost(usage, "deepseek-flash", {"deepseek-flash": (2.0, 8.0)})
        == 0.006
    )


def test_estimate_cost_uses_default_prices():
    assert estimate_cost(Usage(1000, 500, 1500), "deepseek-flash") == 0.006


def test_estimate_cost_rejects_unknown_model():
    with pytest.raises(ValueError):
        estimate_cost(Usage(1, 1, 2), "unknown-model")


def test_usage_from_message_prefers_usage_metadata():
    message = AIMessage(
        content="x",
        usage_metadata={
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
        },
    )
    assert usage_from_message(message) == Usage(10, 5, 15)


def test_usage_from_message_reads_response_metadata():
    message = AIMessage(
        content="x",
        response_metadata={
            "token_usage": {
                "prompt_tokens": 8,
                "completion_tokens": 4,
                "total_tokens": 12,
            }
        },
    )
    assert usage_from_message(message) == Usage(8, 4, 12)


def test_usage_from_message_without_usage():
    assert usage_from_message(AIMessage(content="x")) == Usage(0, 0, 0)


def test_metrics_summary_p50_p95():
    recorder = MetricsRecorder()
    for latency in (10, 20, 30, 40):
        recorder.record("turn", latency)
    summary = recorder.summary()
    assert summary["count"] == 4
    assert summary["p50_ms"] == 25
    assert summary["p95_ms"] == 40
    assert summary["total_tokens"] == 0
    assert summary["total_cost"] == 0.0


def test_metrics_summary_accumulates_usage():
    recorder = MetricsRecorder()
    recorder.record("turn", 10, Usage(1000, 500, 1500))
    recorder.record("turn", 20, Usage(1000, 500, 1500))
    summary = recorder.summary()
    assert summary["total_tokens"] == 3000
    assert summary["total_cost"] == 0.012
