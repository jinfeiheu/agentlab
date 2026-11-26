"""生成文本指标:token F1 与 Exact Match(中文用 jieba 分词)。"""

from collections import Counter

from agentlab.rag_agent.rag.retrieval import tokenize


def token_f1(prediction: str, reference: str) -> float:
    """按词袋重叠计算 token F1;两边都为空时视为完全匹配。"""
    pred_tokens = tokenize(prediction)
    ref_tokens = tokenize(reference)
    if not pred_tokens and not ref_tokens:
        return 1.0
    if not pred_tokens or not ref_tokens:
        return 0.0
    overlap = sum((Counter(pred_tokens) & Counter(ref_tokens)).values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(pred_tokens)
    recall = overlap / len(ref_tokens)
    return 2 * precision * recall / (precision + recall)


def exact_match(prediction: str, reference: str) -> bool:
    """分词后的序列完全一致;忽略空白和纯标点差异。"""
    return tokenize(prediction) == tokenize(reference)
