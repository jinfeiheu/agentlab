"""预算测试：步骤、token、成本、时间和并发。"""

from agentlab.analytics.budget import Budget


def test_budget_consumes_and_exhausts():
    budget = Budget(
        max_steps=2,
        max_tokens=100,
        max_cost=1.0,
        deadline_s=10,
        clock=lambda: 0.0,
        started_at=0.0,
    )

    assert budget.exhausted() is False
    budget.consume(steps=1, tokens=50, cost=0.5)
    assert budget.exhausted() is False
    budget.consume(steps=1, tokens=60, cost=0.6)
    assert budget.exhausted() is True


def test_budget_deadline():
    now = [0.0]
    budget = Budget(
        deadline_s=5,
        clock=lambda: now[0],
        started_at=0.0,
    )

    assert budget.exhausted() is False
    now[0] = 6.0
    assert budget.exhausted() is True


def test_budget_max_concurrency():
    budget = Budget(max_concurrency=2)

    assert budget.max_concurrency == 2
