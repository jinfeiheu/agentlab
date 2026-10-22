from langchain_core.documents import Document
from langchain_core.messages import AIMessage, ToolMessage

from eval.data import GoldenItem
from eval.judge import JudgeResult
from eval.run_eval import _is_refusal, evaluate, write_report
from tests.fakes import FakeRetriever, FakeRunnable


class FakeEvalGraph:
    def invoke(self, payload, config=None, **kwargs):
        question = payload["messages"][0][1]
        if "营收" in question:
            return {"messages": [AIMessage(content="根据现有资料无法回答。")]}
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "search_docs",
                            "args": {"query": question},
                            "id": "c1",
                        }
                    ],
                ),
                ToolMessage(content="ctx", name="search_docs", tool_call_id="c1"),
                AIMessage(content="答案 [来源:02-langgraph.md#Checkpointer]"),
            ]
        }


def _golden():
    return [
        GoldenItem(
            id="g1",
            question="checkpointer 是什么?",
            answerable=True,
            expected_sources=["02-langgraph.md#Checkpointer"],
            relevant_chunk_ids=["02-langgraph.md::2"],
            key_points=["保存状态"],
            expected_tools=["search_docs"],
        ),
        GoldenItem(
            id="g2",
            question="公司营收是多少?",
            answerable=False,
            expected_tools=["search_docs"],
        ),
    ]


def _report():
    docs = [
        Document(
            page_content="checkpointer 保存状态",
            metadata={"chunk_id": "02-langgraph.md::2"},
        )
    ]
    judge = FakeRunnable(
        JudgeResult(
            correctness=4,
            faithfulness=5,
            citation_support=True,
            reason="ok",
        )
    )
    return evaluate(FakeEvalGraph(), FakeRetriever(docs), _golden(), judge)


def test_is_refusal_accepts_security_refusal():
    assert _is_refusal("我不能提供生产环境数据库密码。")
    assert _is_refusal("根据现有资料无法回答。")
    assert not _is_refusal("checkpointer 保存状态。")


def test_evaluate_computes_metrics():
    report = _report()
    assert len(report.rows) == 2
    assert report.retrieval["recall@3"] == 1.0
    assert report.generation["task_success"] == 1.0
    assert report.generation["tool_accuracy"] == 1.0
    assert report.generation["refusal_rate"] == 1.0
    assert report.generation["avg_search_calls"] == 1.0
    assert report.rows[0]["actual_tools"] == ["search_docs"]
    assert report.rows[1]["refused"] is True


def test_retrieval_metrics_use_pre_retrieval_not_tool_results():
    docs = [
        Document(
            page_content="pre",
            metadata={
                "source": "pre.md",
                "section": "pre",
                "chunk_id": "pre.md::0",
            },
        )
    ]
    golden = [
        GoldenItem(
            id="g1",
            question="q",
            answerable=True,
            relevant_chunk_ids=["pre.md::0"],
            expected_tools=["search_docs"],
        )
    ]

    class GraphWithToolResult:
        def invoke(self, payload, config=None, **kwargs):
            return {
                "messages": [
                    ToolMessage(
                        content="[来源:tool.md#tool]\ntool",
                        name="search_docs",
                        tool_call_id="c1",
                    ),
                    AIMessage(content="answer"),
                ]
            }

    judge = FakeRunnable(
        JudgeResult(
            correctness=4,
            faithfulness=4,
            citation_support=True,
            reason="ok",
        )
    )
    report = evaluate(
        GraphWithToolResult(),
        FakeRetriever(docs),
        golden,
        judge,
    )
    assert report.rows[0]["retrieved_ids"] == ["pre.md::0"]
    assert report.rows[0]["pre_retrieval_labels"] == ["pre.md#pre"]
    assert report.rows[0]["evidence_labels"] == ["tool.md#tool"]
    assert report.retrieval["recall@3"] == 1.0


def test_evaluate_passes_tool_results_to_judge():
    class RecordingJudge:
        prompts = []

        def invoke(self, prompt):
            self.prompts.append(prompt)
            return JudgeResult(
                correctness=4,
                faithfulness=4,
                citation_support=True,
                reason="ok",
            )

    docs = [
        Document(
            page_content="checkpointer 保存状态",
            metadata={"chunk_id": "02-langgraph.md::2"},
        )
    ]
    judge = RecordingJudge()
    evaluate(FakeEvalGraph(), FakeRetriever(docs), _golden(), judge)
    assert any("ctx" in prompt for prompt in judge.prompts)


def test_write_report_creates_markdown_and_json(tmp_path):
    path = tmp_path / "results" / "baseline.md"
    write_report(_report(), path)
    assert path.exists()
    assert path.with_suffix(".json").exists()
    markdown = path.read_text(encoding="utf-8")
    assert "task_success" in markdown
    assert "g1" in markdown
    json_text = path.with_suffix(".json").read_text(encoding="utf-8")
    assert '"generation"' in json_text
