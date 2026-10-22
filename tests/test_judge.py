from eval.judge import JudgeResult, build_judge, judge_answer
from tests.fakes import FailingRunnable, FakeRunnable


def test_build_judge_uses_json_mode(monkeypatch):
    calls = {}

    class FakeModel:
        def with_structured_output(self, schema, **kwargs):
            calls["schema"] = schema
            calls["method"] = kwargs.get("method")
            return FakeRunnable(
                JudgeResult(
                    correctness=3,
                    faithfulness=3,
                    citation_support=False,
                    reason="fake",
                )
            )

    monkeypatch.setattr("eval.judge.build_judge_model", lambda: FakeModel())
    judge = build_judge()
    assert calls["schema"] is JudgeResult
    assert calls["method"] == "json_mode"
    assert isinstance(judge, FakeRunnable)


def test_judge_returns_structured_result():
    fake = FakeRunnable(
        JudgeResult(
            correctness=4,
            faithfulness=5,
            citation_support=True,
            reason="ok",
        )
    )
    result = judge_answer(fake, "q", "a", ["ctx"])
    assert result.correctness == 4
    assert result.faithfulness == 5
    assert result.citation_support is True
    assert result.reason == "ok"


def test_judge_prompt_includes_key_points():
    class RecordingRunnable:
        prompt = ""

        def invoke(self, prompt):
            self.prompt = prompt
            return JudgeResult(
                correctness=3,
                faithfulness=3,
                citation_support=False,
                reason="fake",
            )

    judge = RecordingRunnable()
    judge_answer(judge, "q", "a", ["ctx"], ["关键点一"])
    assert "关键点一" in judge.prompt


def test_judge_failure_returns_safe_default():
    result = judge_answer(FailingRunnable(), "q", "a", [])
    assert result.correctness == 0
    assert result.faithfulness == 0
    assert result.citation_support is False
    assert "judge failed" in result.reason
