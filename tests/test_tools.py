import os
import subprocess
import sys
from pathlib import Path

from langchain_core.documents import Document

from tools import calculator, make_search_tool

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SUBPROCESS_ENV = {
    **os.environ,
    "OPENBLAS_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
}


def test_calculator_evaluates_expression():
    assert calculator.invoke({"expression": "2+3*4"}) == "14"


def test_calculator_handles_division():
    assert calculator.invoke({"expression": "10/4"}) == "2.5"


def test_calculator_rejects_zero_division():
    assert "除数" in calculator.invoke({"expression": "1/0"})


def test_calculator_rejects_code_execution():
    result = calculator.invoke({"expression": "__import__('os').system('echo hi')"})
    assert result.startswith("错误")


def test_calculator_rejects_huge_exponent():
    assert "指数" in calculator.invoke({"expression": "2**1000000"})


def test_calculator_rejects_nested_huge_power():
    code = """
import resource
resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
from tools import calculator
print(calculator.invoke({"expression": "((9**999)**999)**999"}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=5,
        env=_SUBPROCESS_ENV,
    )
    assert result.returncode == 0
    assert "结果过大" in result.stdout


def test_calculator_rejects_result_too_large():
    assert "结果过大" in calculator.invoke({"expression": "99999**1000"})


class FakeRetriever:
    def __init__(self, docs):
        self.docs = docs

    def invoke(self, query):
        return self.docs


def test_search_tool_formats_results():
    tool = make_search_tool(
        FakeRetriever(
            [Document(page_content="checkpointer 保存状态", metadata={"source": "k.md"})]
        )
    )
    assert tool.name == "search_docs"
    out = tool.invoke({"query": "checkpointer"})
    assert "checkpointer 保存状态" in out
    assert "k.md" in out


def test_search_tool_handles_no_results():
    tool = make_search_tool(FakeRetriever([]))
    assert "没有找到" in tool.invoke({"query": "不存在的内容"})


def test_search_tool_limits_top_n():
    docs = [
        Document(
            page_content=f"内容{i}",
            metadata={"source": f"{i}.md", "section": "S"},
        )
        for i in range(4)
    ]
    tool = make_search_tool(FakeRetriever(docs), top_n=2)
    out = tool.invoke({"query": "x"})
    assert out.count("[来源:") == 2
    assert "内容0" in out and "内容1" in out
    assert "内容2" not in out


def test_search_tool_emits_retrieve_and_rerank_spans():
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from tracing import setup_tracing

    exporter = InMemorySpanExporter()
    setup_tracing(exporter=exporter)
    docs = [
        Document(page_content="a", metadata={"source": "a.md", "section": "S"})
    ]

    class FakeReranker:
        def rerank(self, query, items):
            return list(items)

    tool = make_search_tool(FakeRetriever(docs), reranker=FakeReranker())
    tool.invoke({"query": "q"})
    names = {span.name for span in exporter.get_finished_spans()}
    assert "retrieve" in names
    assert "rerank" in names


def test_search_tool_applies_reranker():
    docs = [
        Document(page_content="a", metadata={"source": "a.md", "section": "S"}),
        Document(page_content="b", metadata={"source": "b.md", "section": "S"}),
    ]

    class FakeReranker:
        def __init__(self):
            self.calls = []

        def rerank(self, query, items):
            self.calls.append((query, items))
            return list(reversed(items))

    reranker = FakeReranker()
    tool = make_search_tool(FakeRetriever(docs), reranker=reranker, top_n=2)
    out = tool.invoke({"query": "q"})
    assert reranker.calls[0][0] == "q"
    assert out.index("b.md") < out.index("a.md")
