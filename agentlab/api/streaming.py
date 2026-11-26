"""共享 SSE 原语：事件编码与输入拒绝事件。"""

import json


def sse(payload: dict) -> str:
    """把一个事件编码成 SSE data 帧。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _refusal_events(message: str):
    """把输入拒绝包装成与正常流一致的 token + done 事件。"""

    async def events():
        yield sse({"type": "token", "text": message})
        yield sse({"type": "done", "sources": []})

    return events()
