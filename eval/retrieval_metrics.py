"""检索指标:Recall@k、MRR、nDCG@k,全部用二元相关性。"""

import math


def recall_at_k(
    retrieved_ids: list[str],
    relevant_ids: set[str],
    k: int,
) -> float:
    """前 k 个结果覆盖了多少比例的相关 chunk。"""
    relevant = set(relevant_ids)
    if not relevant or k <= 0:
        return 0.0
    return len(set(retrieved_ids[:k]) & relevant) / len(relevant)


def reciprocal_rank(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    """单条查询的 reciprocal rank:第一个相关结果排名的倒数。"""
    relevant = set(relevant_ids)
    for rank, chunk_id in enumerate(retrieved_ids, 1):
        if chunk_id in relevant:
            return 1.0 / rank
    return 0.0


def mrr(rows: list[dict]) -> float:
    """多条查询的平均 reciprocal rank(Mean Reciprocal Rank)。"""
    if not rows:
        return 0.0
    return sum(
        reciprocal_rank(row["retrieved_ids"], set(row["relevant_ids"]))
        for row in rows
    ) / len(rows)


def ndcg_at_k(
    retrieved_ids: list[str],
    relevant_ids: set[str],
    k: int,
) -> float:
    """二元相关性的归一化折损累计增益。"""
    relevant = set(relevant_ids)
    if not relevant or k <= 0:
        return 0.0
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, chunk_id in enumerate(retrieved_ids[:k], 1)
        if chunk_id in relevant
    )
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def aggregate(rows: list[dict], k: int) -> dict[str, float]:
    """对多条样本的检索指标取平均。"""
    if not rows:
        return {
            "count": 0,
            f"recall@{k}": 0.0,
            "mrr": 0.0,
            f"ndcg@{k}": 0.0,
        }
    count = len(rows)
    return {
        "count": count,
        f"recall@{k}": sum(
            recall_at_k(row["retrieved_ids"], set(row["relevant_ids"]), k)
            for row in rows
        )
        / count,
        "mrr": mrr(rows),
        f"ndcg@{k}": sum(
            ndcg_at_k(row["retrieved_ids"], set(row["relevant_ids"]), k)
            for row in rows
        )
        / count,
    }
