"""Analytics CLI 输出格式测试。"""

from agentlab.analytics.cli import build_parser, format_state


def test_format_state_includes_answer_sql_table_and_chart():
    state = {
        "answer": "收入为 100。",
        "sql": "SELECT 100 AS revenue",
        "result": {
            "columns": ["revenue"],
            "rows": [[100]],
            "truncated": False,
        },
        "chart_spec": {"mark": "bar", "data": {"values": []}},
    }

    text = format_state(state)

    assert "收入为 100。" in text
    assert "SELECT 100 AS revenue" in text
    assert "revenue" in text and "100" in text
    assert "Chart" in text


def test_format_state_shows_clarification():
    text = format_state({"clarification": "请明确时间范围。"})
    assert "请明确时间范围" in text


def test_cli_parser_defaults():
    args = build_parser().parse_args(["2026 年 9 月收入"])
    assert args.tenant == "tenant_a"
    assert args.session == "cli"
    assert args.json is False
