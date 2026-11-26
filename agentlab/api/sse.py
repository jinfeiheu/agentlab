"""SSE 事件、文本/来源提取与流式生成器。"""

import asyncio
import json
import logging
import re
import time
from contextlib import aclosing

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from agentlab.rag_agent.context import compress_tool_content
from agentlab.api.services import _post_turn_memory, _prepare_thread
from agentlab.security.guard import StreamingRedactor, redact_pii

_SOURCE_RE = re.compile(r"\[来源:([^\]]+)\]")
_TOOL_RESULT_CHARS = 500

logger = logging.getLogger(__name__)


def sse(payload: dict) -> str:
    """把一个事件编码成 SSE data 帧。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _refusal_events(message: str):
    """把输入拒绝包装成与正常流一致的 token + done 事件。"""

    async def events():
        yield sse({"type": "token", "text": message})
        yield sse({"type": "done", "sources": []})

    return events()


def _content_text(content) -> str:
    """把 str 或内容块列表统一成字符串。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "".join(parts)
    return ""


def _message_text(message) -> str:
    content = (
        message.get("content")
        if isinstance(message, dict)
        else getattr(message, "content", None)
    )
    return _content_text(content)


def _extract_answer(result) -> str:
    """取最后一条有内容的 AI 消息。"""
    messages = result.get("messages", []) if isinstance(result, dict) else []
    for message in reversed(messages):
        role = (
            message.get("type")
            if isinstance(message, dict)
            else getattr(message, "type", None)
        )
        if role not in ("ai", "assistant"):
            continue
        text = _message_text(message)
        if text.strip():
            return redact_pii(text)
    return ""


def _sources_from_text(text: str) -> list[str]:
    """提取 [来源:...] 标记。"""
    return [item.strip() for item in _SOURCE_RE.findall(text) if item.strip()]


def _dedupe(items) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _extract_sources(result) -> list[str]:
    """从 ToolMessage 和回答中收集来源。"""
    messages = result.get("messages", []) if isinstance(result, dict) else []
    return _dedupe(
        redact_pii(source)
        for message in messages
        for source in _sources_from_text(_message_text(message))
    )


def _interrupt_payload(state) -> dict | None:
    """把 LangGraph 的 interrupt 状态整理成前端可用的事件。"""
    interrupts = getattr(state, "interrupts", ()) or ()
    if not interrupts:
        return None
    value = getattr(interrupts[0], "value", None)
    if isinstance(value, dict):
        return {
            "question": redact_pii(str(value.get("question", ""))),
            "content": redact_pii(str(value.get("content", ""))),
        }
    return {"question": redact_pii(str(value or "")), "content": ""}


async def _has_interrupt(graph, config) -> bool:
    """线程是否有 pending interrupt;fake graph 没有 aget_state 时视为没有。"""
    aget_state = getattr(graph, "aget_state", None)
    if aget_state is None:
        return False
    state = await aget_state(config)
    return bool(getattr(state, "interrupts", ()))


async def _get_interrupt(graph, config) -> dict | None:
    """读取线程当前的 pending interrupt;fake graph 没有 aget_state 时返回 None。"""
    aget_state = getattr(graph, "aget_state", None)
    if aget_state is None:
        return None
    try:
        state = await aget_state(config)
    except Exception as exc:  # noqa: BLE001 - 读状态失败不影响已有回答
        logger.warning("读取 interrupt 状态失败: %s", redact_pii(str(exc)))
        return None
    return _interrupt_payload(state)


def _redact_value(value):
    """递归脱敏工具参数/结果里的字符串,前端展示不出现原始 PII。"""
    if isinstance(value, str):
        return redact_pii(value)
    if isinstance(value, dict):
        return {key: _redact_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_value(item) for item in value]
    return value


def _tool_events(message) -> list[dict]:
    """把一条消息转换成 tool_call / tool_result 事件。"""
    events: list[dict] = []
    for call in getattr(message, "tool_calls", None) or []:
        events.append(
            {
                "type": "tool_call",
                "id": call.get("id") or "",
                "name": call.get("name", ""),
                "args": _redact_value(call.get("args", {})),
            }
        )
    if isinstance(message, ToolMessage) or getattr(message, "type", None) == "tool":
        events.append(
            {
                "type": "tool_result",
                "tool_call_id": getattr(message, "tool_call_id", "") or "",
                "name": getattr(message, "name", ""),
                "content": compress_tool_content(
                    redact_pii(_message_text(message)), _TOOL_RESULT_CHARS
                ),
            }
        )
    return events


async def _chat_events(
    graph,
    payload,
    config,
    request,
    timeout,
    lock,
    context=None,
    services=None,
    user_text: str = "",
    skip_prepare: bool = False,
):
    """把 graph 流转换成 SSE 事件;负责串行、修复、超时、断连和异常上报。"""
    sources: list[str] = []
    answer_parts: list[str] = []
    redactor = StreamingRedactor()
    try:
        async with lock:
            deadline = time.monotonic() + timeout
            if skip_prepare:
                remaining = max(0.01, deadline - time.monotonic())
                try:
                    has_interrupt = await asyncio.wait_for(
                        _has_interrupt(graph, config), timeout=remaining
                    )
                except asyncio.TimeoutError:
                    yield sse(
                        {"type": "error", "message": "request timeout"}
                    )
                    return
                if not has_interrupt:
                    yield sse(
                        {"type": "error", "message": "no pending interrupt"}
                    )
                    return
            else:
                remaining = max(0.01, deadline - time.monotonic())
                try:
                    await asyncio.wait_for(
                        _prepare_thread(graph, config), timeout=remaining
                    )
                except asyncio.TimeoutError:
                    yield sse(
                        {"type": "error", "message": "request timeout"}
                    )
                    return

            async with aclosing(
                graph.astream(
                    payload,
                    config=config,
                    context=context,
                    stream_mode=["messages", "updates"],
                )
            ) as stream:
                iterator = stream.__aiter__()
                while True:
                    if await request.is_disconnected():
                        return
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        yield sse(
                            {"type": "error", "message": "request timeout"}
                        )
                        return
                    try:
                        mode, data = await asyncio.wait_for(
                            iterator.__anext__(), timeout=remaining
                        )
                    except StopAsyncIteration:
                        break
                    except asyncio.TimeoutError:
                        yield sse(
                            {"type": "error", "message": "request timeout"}
                        )
                        return
                    if mode == "messages":
                        chunk, _metadata = data
                        if not isinstance(chunk, (AIMessage, AIMessageChunk)):
                            continue
                        text = _message_text(chunk)
                        if text:
                            answer_parts.append(text)
                            safe = redactor.feed(text)
                            if safe:
                                yield sse({"type": "token", "text": safe})
                    elif mode == "updates":
                        for update in (data or {}).values():
                            if not isinstance(update, dict):
                                continue
                            for message in update.get("messages", []):
                                if isinstance(message, ToolMessage) or getattr(
                                    message, "type", None
                                ) == "tool":
                                    sources.extend(
                                        _sources_from_text(_message_text(message))
                                    )
                                for event in _tool_events(message):
                                    yield sse(event)
            tail = redactor.flush()
            if tail:
                yield sse({"type": "token", "text": tail})
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                yield sse({"type": "error", "message": "request timeout"})
                return
            try:
                interrupt = await asyncio.wait_for(
                    _get_interrupt(graph, config), timeout=remaining
                )
            except asyncio.TimeoutError:
                yield sse({"type": "error", "message": "request timeout"})
                return
            if interrupt:
                yield sse({"type": "interrupt", **interrupt})
            elif services is not None and user_text:
                remaining = deadline - time.monotonic()
                if remaining > 0:
                    try:
                        await asyncio.wait_for(
                            _post_turn_memory(
                                graph,
                                config,
                                services,
                                context,
                                user_text,
                            ),
                            timeout=remaining,
                        )
                    except asyncio.TimeoutError:
                        logger.warning(
                            "流式轮次结束后记忆抽取超时,已跳过"
                        )
            yield sse(
                {
                    "type": "done",
                    "sources": _dedupe(
                        redact_pii(source)
                        for source in (
                            sources
                            + _sources_from_text("".join(answer_parts))
                        )
                    ),
                }
            )
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - 生成器内错误统一发 error 事件
        yield sse({"type": "error", "message": redact_pii(str(exc))})
