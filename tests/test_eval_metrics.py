import math

import pytest

from eval.retrieval_metrics import (
    aggregate,
    mrr,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_recall_at_k():
    assert recall_at_k(["a", "b", "c"], {"b", "d"}, 2) == 0.5
    assert recall_at_k(["a", "b"], {"b"}, 2) == 1.0
    assert recall_at_k(["a"], {"b"}, 1) == 0.0


def test_reciprocal_rank():
    assert reciprocal_rank(["a", "b", "c"], {"b"}) == 0.5
    assert reciprocal_rank(["a", "b", "c"], {"c"}) == pytest.approx(1 / 3)
    assert reciprocal_rank(["a"], {"b"}) == 0.0


def test_mrr():
    rows = [
        {"retrieved_ids": ["a", "b"], "relevant_ids": {"a"}},
        {"retrieved_ids": ["c", "d"], "relevant_ids": {"d"}},
        {"retrieved_ids": ["e"], "relevant_ids": {"f"}},
    ]
    assert mrr(rows) == pytest.approx(0.5)
    assert mrr([]) == 0.0


def test_ndcg_at_k():
    assert ndcg_at_k(["a", "b"], {"b"}, 2) == pytest.approx(1 / math.log2(3))
    assert ndcg_at_k(["b", "a"], {"b"}, 2) == 1.0
    assert ndcg_at_k(["a", "b", "c"], {"c"}, 3) == pytest.approx(0.5)
    assert ndcg_at_k(["a"], {"b"}, 1) == 0.0


def test_ndcg_at_k_multi_relevant():
    assert ndcg_at_k(["a", "b", "c"], {"b", "d"}, 2) == pytest.approx(
        (1 / math.log2(3)) / (1 + 1 / math.log2(3))
    )


def test_aggregate_means():
    rows = [
        {"retrieved_ids": ["a", "b"], "relevant_ids": {"a"}},
        {"retrieved_ids": ["c", "d"], "relevant_ids": {"d"}},
    ]
    result = aggregate(rows, 2)
    assert result["count"] == 2
    assert result["recall@2"] == 1.0
    assert result["mrr"] == 0.75
    assert result["ndcg@2"] == pytest.approx((1.0 + 1 / math.log2(3)) / 2)


def test_aggregate_empty():
    assert aggregate([], 3) == {
        "count": 0,
        "recall@3": 0.0,
        "mrr": 0.0,
        "ndcg@3": 0.0,
    }
