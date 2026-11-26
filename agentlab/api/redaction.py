"""API 出口的统一递归脱敏。"""

from typing import Any

from agentlab.security.guard import redact_pii


def redact_value(value: Any) -> Any:
    """递归脱敏字符串里的 PII。"""
    if isinstance(value, str):
        return redact_pii(value)
    if isinstance(value, dict):
        return {key: redact_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_value(item) for item in value]
    return value
