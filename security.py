"""安全边界:提示注入检测、PII 脱敏与工具 allowlist。

这里用启发式规则做最小演示;生产环境应替换为分类模型或规则引擎,
并保留同样的接口(输入检查、PII 脱敏、工具策略)。
"""

import re
from dataclasses import dataclass

from langchain_core.messages import ToolMessage
from langgraph.types import Command

# 工具白名单:公开只读工具 + 本地 HITL/私有数据工具。
# list_sources/doc_stats/word_count 来自 Task 12.5 的 MCP server,USE_MCP=true 时会进入图。
ALLOWED_TOOLS = frozenset(
    {
        "search_docs",
        "list_sources",
        "doc_stats",
        "calculator",
        "word_count",
        "search_memory",
        "get_ticket",
        "send_report",
        "save_memory",
    }
)

# 中英文提示注入启发式;宁可误拒,也不把控制指令透传给模型。
_INJECTION_PATTERNS = (
    re.compile(
        r"忽略(?:之前|以上|前面|先前|此前)的?(?:所有)?(?:指令|指示|规则|要求)"
    ),
    re.compile(
        r"ignore\s+(?:all\s+)?(?:the\s+)?(?:previous|prior|above)\s+"
        r"(?:instructions|rules|prompts)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:泄露|透露|显示|打印|输出|复述).{0,8}"
        r"(?:系统提示词?|system\s*prompt|提示词)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:系统提示词?|system\s*prompt|提示词).{0,8}"
        r"(?:发给我|告诉我|泄露|透露|输出|打印|显示)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:你现在是|从现在开始你是|从现在起你是|"
        r"pretend\s+to\s+be|act\s+as\s+an?\s+unrestricted)",
        re.IGNORECASE,
    ),
    re.compile(r"(?:越狱|jailbreak|developer\s+mode|DAN\s*模式)", re.IGNORECASE),
)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# 18 位身份证(末位可为 X);先于银行卡替换,避免被 16-19 位规则吃掉。
_ID_RE = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
_CARD_RE = re.compile(r"(?<!\d)\d{16,19}(?!\d)")
_PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")


@dataclass(frozen=True)
class SecurityDecision:
    """输入检查结果;allowed 为 False 时 reason 是可直接展示的中文原因。"""

    allowed: bool
    reason: str = ""


class ToolDenied(Exception):
    """工具调用未通过安全策略。"""


def check_input(text: str) -> SecurityDecision:
    """检查用户输入是否包含疑似提示注入。"""
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text or ""):
            return SecurityDecision(
                allowed=False,
                reason="检测到疑似提示注入,请求已被拒绝。",
            )
    return SecurityDecision(allowed=True)


def redact_pii(text: str) -> str:
    """把常见 PII 替换成类型占位符,用于日志、trace 与页面展示。"""
    if not text:
        return text
    redacted = _EMAIL_RE.sub("[EMAIL]", text)
    redacted = _ID_RE.sub("[ID]", redacted)
    redacted = _CARD_RE.sub("[CARD]", redacted)
    return _PHONE_RE.sub("[PHONE]", redacted)


def check_tool(name: str, args: dict) -> None:
    """只放行 allowlist 中的工具;未知工具或非法参数抛 ToolDenied。"""
    if name not in ALLOWED_TOOLS:
        raise ToolDenied(f"工具 {name} 不在允许列表中")
    if not isinstance(args, dict):
        raise ToolDenied(f"工具 {name} 的参数必须是对象")


def ensure_tools_allowed(tools) -> None:
    """启动时校验注册工具都在白名单内,防止工具清单与策略漂移。"""
    names = set()
    for tool in tools:
        name = getattr(tool, "name", None) or getattr(tool, "__name__", None)
        names.add(name or type(tool).__name__)
    unlisted = sorted(names - ALLOWED_TOOLS)
    if unlisted:
        raise RuntimeError(f"工具未通过安全白名单:{unlisted}")


def _denied_message(request, exc: ToolDenied) -> ToolMessage:
    """把拒绝原因包装成模型可读的 ToolMessage,保持 tool_call_id 对齐。"""
    tool_call = request.tool_call
    return ToolMessage(
        content=f"工具调用被拒绝:{exc}",
        tool_call_id=tool_call["id"],
        name=tool_call["name"],
    )


def security_wrapper(request, execute) -> ToolMessage | Command:
    """同步工具包装器:先过 allowlist,未授权时不执行工具。"""
    try:
        check_tool(request.tool_call["name"], request.tool_call.get("args", {}))
    except ToolDenied as exc:
        return _denied_message(request, exc)
    return execute(request)


async def asecurity_wrapper(request, execute) -> ToolMessage | Command:
    """异步工具包装器;与同步版本保持同样的拒绝语义。"""
    try:
        check_tool(request.tool_call["name"], request.tool_call.get("args", {}))
    except ToolDenied as exc:
        return _denied_message(request, exc)
    return await execute(request)
