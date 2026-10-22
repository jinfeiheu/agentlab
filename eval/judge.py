"""LLM-as-judge:结构化评分,失败时返回安全默认值。"""

from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from models import build_judge_model


class JudgeResult(BaseModel):
    """裁判对一条回答的评分。"""

    correctness: int = Field(ge=0, le=5)
    faithfulness: int = Field(ge=0, le=5)
    citation_support: bool
    reason: str


JUDGE_PROMPT = """你是严格的 RAG 评测裁判。请根据问题、回答和检索上下文评分,只输出 JSON,不要输出其他文字。
JSON 字段:
- correctness: 0-5 的整数。回答是否真正回答了问题,关键事实是否正确;资料不足时,是否明确说明无法回答。
- faithfulness: 0-5 的整数。回答是否只依据检索上下文,是否出现上下文不支持的内容。
- citation_support: 布尔值。回答中的来源引用是否真的被上下文支持;没有引用时为 false。
- reason: 用一句话说明理由。

问题:
{question}

期望关键点:
{key_points}

回答:
{answer}

检索上下文:
{contexts}
"""


def build_judge() -> Runnable:
    """创建结构化输出的裁判模型。

    deepseek-flash 的 thinking mode 不支持 tool_choice,
    因此使用 JSON mode,而不是默认的 function_calling。
    """
    return build_judge_model().with_structured_output(
        JudgeResult,
        method="json_mode",
    )


def judge_answer(
    judge: Runnable,
    question: str,
    answer: str,
    contexts: list[str],
    key_points: list[str] | None = None,
) -> JudgeResult:
    """评分;任何异常都转成安全默认值,保证评测不中断。"""
    context_text = "\n\n---\n\n".join(contexts) if contexts else "（无检索上下文）"
    key_points_text = (
        "\n".join(f"- {point}" for point in key_points)
        if key_points
        else "（无）"
    )
    prompt = JUDGE_PROMPT.format(
        question=question,
        key_points=key_points_text,
        answer=answer,
        contexts=context_text,
    )
    try:
        result = judge.invoke(prompt)
        if isinstance(result, JudgeResult):
            return result
        return JudgeResult.model_validate(result)
    except Exception as exc:
        return JudgeResult(
            correctness=0,
            faithfulness=0,
            citation_support=False,
            reason=f"judge failed: {exc}",
        )
