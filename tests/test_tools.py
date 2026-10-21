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
