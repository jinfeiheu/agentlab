"""LLM-as-judge:结构化评分,失败时返回安全默认值。"""

from langchain_core.runnables import Runnable
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from config import DEEPSEEK_MODEL, EVAL_JUDGE_MODEL, OLLAMA_BASE_URL
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
  如果提供了参考答案,以回答是否覆盖参考答案中的关键事实为准,不要因为措辞不同扣分。
- faithfulness: 0-5 的整数。回答是否只依据检索上下文,是否出现上下文不支持的内容。
- citation_support: 布尔值。回答中的来源引用是否真的被上下文支持;没有引用时为 false。
- reason: 用一句话说明理由。

严格性要求:
- 多跳问题必须同时覆盖多个来源的事实,只答对一半最多 3 分。
- 涉及版本/时间的问题,必须使用当前有效版本,引用已废弃版本的关键事实不算正确。
- 不可回答问题必须在存在干扰证据时仍然拒答;使用干扰证据编造答案记 0 分。
- 数值/表格问题必须与参考答案的数值和单位一致。

问题:
{question}

期望关键点:
{key_points}

参考答案:
{reference_answer}

回答:
{answer}

检索上下文:
{contexts}
"""

_DEEPSEEK_ALIASES = {DEEPSEEK_MODEL, "deepseek", "deepseek-flash"}


def build_judge(model_name: str | None = None) -> Runnable:
    """创建结构化输出的裁判模型。

    deepseek-flash 的 thinking mode 不支持 tool_choice,
    因此使用 JSON mode,而不是默认的 function_calling。
    传入本地 Ollama 模型名时用同一 schema 做跨模型对照。
    """
    name = model_name or EVAL_JUDGE_MODEL
    if name in _DEEPSEEK_ALIASES:
        model = build_judge_model()
    else:
        model = ChatOllama(
            model=name,
            temperature=0,
            reasoning=False,
            base_url=OLLAMA_BASE_URL,
        )
    return model.with_structured_output(
        JudgeResult,
        method="json_mode",
    )


def judge_answer(
    judge: Runnable,
    question: str,
    answer: str,
    contexts: list[str],
    key_points: list[str] | None = None,
    reference_answer: str | None = None,
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
        reference_answer=reference_answer or "（无，按关键点与上下文评分）",
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
