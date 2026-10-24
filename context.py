"""上下文工程:token 估算、历史裁剪与工具结果压缩。"""

from langchain_core.messages import BaseMessage

# CJK 统一表意文字范围 U+4E00–U+9FFF
_CJK_START = 0x4E00
_CJK_END = 0x9FFF
_TRUNCATED_SUFFIX = "...(已截断)"
_ROLE_NAMES = {
    "system": "系统",
    "human": "用户",
    "ai": "助手",
    "tool": "工具",
}


def estimate_tokens(text: str) -> int:
    """近似 token 数:中文字符按 1,其它按 4 字符/token,向上取整。"""
    if not text:
        return 0
    cjk = sum(1 for char in text if _CJK_START <= ord(char) <= _CJK_END)
    other = len(text) - cjk
    return max(1, cjk + (other + 3) // 4)


def _message_text(message: BaseMessage) -> str:
    """把消息内容统一成字符串;多模态内容块也会被串起来估算。"""
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    return str(content)


def _message_cost(message: BaseMessage) -> int:
    return estimate_tokens(_message_text(message))


def _group_messages(messages: list[BaseMessage]) -> list[list[BaseMessage]]:
    """把 ToolMessage 并入前一条消息组,避免裁剪后出现孤立工具结果。"""
    groups: list[list[BaseMessage]] = []
    for message in messages:
        if getattr(message, "type", None) == "tool" and groups:
            groups[-1].append(message)
        else:
            groups.append([message])
    return groups


def trim_messages(
    messages: list[BaseMessage], max_tokens: int
) -> list[BaseMessage]:
    """保留全部 system 消息和最近的对话组,超预算时从最旧的组开始丢。

    工具调用与它的 ToolMessage 始终作为一组保留或丢弃;最新一组即使
    超过预算也会保留,保证模型至少能看到当前问题。
    """
    system = [
        message for message in messages if getattr(message, "type", None) == "system"
    ]
    conversation = [
        message
        for message in messages
        if getattr(message, "type", None) != "system"
    ]
    if not conversation:
        return system

    groups = _group_messages(conversation)
    remaining = max_tokens - sum(_message_cost(message) for message in system)
    kept: list[list[BaseMessage]] = []
    for group in reversed(groups):
        cost = sum(_message_cost(message) for message in group)
        if kept and cost > remaining:
            break
        kept.append(group)
        remaining -= cost
    if not kept:
        kept = [groups[-1]]
    kept.reverse()
    return system + [message for group in kept for message in group]


def plan_compaction(
    messages: list[BaseMessage], max_tokens: int
) -> tuple[list[BaseMessage], list[BaseMessage]] | None:
    """超过预算时返回 (old, recent);old 可以摘要后从状态删除。

    system 消息不参与切分,也不会被删除;工具调用与其结果始终同组。
    """
    system = [
        message for message in messages if getattr(message, "type", None) == "system"
    ]
    conversation = [
        message
        for message in messages
        if getattr(message, "type", None) != "system"
    ]
    if not conversation:
        return None
    total = sum(_message_cost(message) for message in messages)
    if total <= max_tokens:
        return None

    groups = _group_messages(conversation)
    if len(groups) < 2:
        return None

    system_cost = sum(_message_cost(message) for message in system)
    available = max(1, max_tokens - system_cost)
    recent_budget = max(1, available // 2)
    kept: list[list[BaseMessage]] = []
    used = 0
    for group in reversed(groups):
        cost = sum(_message_cost(message) for message in group)
        if kept and used + cost > recent_budget:
            break
        kept.append(group)
        used += cost
    kept.reverse()

    old_count = len(groups) - len(kept)
    if old_count <= 0:
        return None
    old = [message for group in groups[:old_count] for message in group]
    recent = [message for group in kept for message in group]
    return old, recent


def compress_tool_content(text: str, max_chars: int = 600) -> str:
    """截断过长的工具结果,保留开头并显式标注。"""
    max_chars = max(0, max_chars)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + _TRUNCATED_SUFFIX


def summarize_messages(model, messages: list[BaseMessage]) -> str:
    """用一次模型调用把对话压缩成中文摘要。"""
    if not messages:
        return ""
    lines = []
    for message in messages:
        role = _ROLE_NAMES.get(getattr(message, "type", ""), "消息")
        lines.append(f"{role}:{_message_text(message)}")
    prompt = (
        "请把下面的对话压缩成一段简洁的中文摘要,保留用户偏好、"
        "事实和未完成事项,不要编造:\n\n" + "\n".join(lines)
    )
    result = model.invoke(prompt)
    content = getattr(result, "content", result)
    if isinstance(content, list):
        content = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content)
