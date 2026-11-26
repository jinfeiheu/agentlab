"""单 Agent 图构建:手写 StateGraph 与 create_agent 两种写法。"""

from langchain.agents import create_agent
from langchain_core.messages import RemoveMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.runtime import Runtime

from agentlab.rag_agent.context import (
    estimate_tokens,
    plan_compaction,
    summarize_messages,
    trim_messages,
)
from agentlab.rag_agent.memory import load_profile, save_episode
from agentlab.config import CONTEXT_MAX_TOKENS, ENABLE_AUTO_MEMORY
from agentlab.security.auth import UserContext
from agentlab.security.guard import asecurity_wrapper, ensure_tools_allowed, security_wrapper

SYSTEM_PROMPT = """你是一个中文技术问答助手,回答要简洁、准确。

工具使用规则:
1. 回答 LangChain、LangGraph、RAG、Agent 等技术问题时,先调用 search_docs 检索本地知识库。
2. 只依据检索到的片段回答,不要用片段之外的知识补充事实;片段不足以回答时,直接说“根据现有资料无法回答”。
3. 引用时在句末标注来源,格式为 [来源:文件名#章节]。
4. 需要算术时调用 calculator,不要心算。
5. 用户要求发送报告时,把要发送的内容传给 send_report;该工具会请求人工确认。
6. 查询工单时调用 get_ticket;只能查询当前用户自己的工单,不要猜测其他用户的数据。
7. 用户要求记住偏好或事实时调用 save_memory,key 用点分格式,例如 profile.name、preference.color;回答涉及用户已知信息时先调用 search_memory。
8. 长期记忆只保存用户明确要求记住的内容,不要猜测或保存敏感信息。
"""


# 超过该比例的上下文预算就先摘要压缩,避免 agent 裁剪时直接丢信息。
_COMPACT_RATIO = 0.8


class AgentState(MessagesState):
    """手写图状态:消息 + 较早对话的滚动摘要。"""

    summary: str


def build_graph(model, tools, checkpointer=None, store=None):
    """手写 LangGraph:压缩 -> agent -> tools 循环,直到模型不再调用工具。"""
    ensure_tools_allowed(tools)
    llm = model.bind_tools(tools)

    def compact(
        state: AgentState,
        config: RunnableConfig,
        runtime: Runtime[UserContext],
    ):
        """超过阈值时把旧消息摘要进 state.summary,并从状态删除旧消息。"""
        summary = state.get("summary", "")
        threshold = max(1, int(CONTEXT_MAX_TOKENS * _COMPACT_RATIO))
        budget = max(1, threshold - estimate_tokens(summary))
        plan = plan_compaction(state["messages"], budget)
        if plan is None:
            return {}
        old, _recent = plan
        summary_input = []
        if summary:
            summary_input.append(
                SystemMessage(content=f"已有对话摘要:\n{summary}")
            )
        summary_input.extend(old)
        new_summary = summarize_messages(model, summary_input)
        if not new_summary:
            return {}

        context = getattr(runtime, "context", None)
        user_id = getattr(context, "user_id", "")
        store = getattr(runtime, "store", None)
        if ENABLE_AUTO_MEMORY and store is not None and user_id:
            thread_id = (config.get("configurable") or {}).get(
                "thread_id", ""
            )
            try:
                save_episode(
                    store, user_id, new_summary, thread_id=thread_id
                )
            except Exception:  # noqa: BLE001 - 记忆失败不影响压缩
                pass

        return {
            "summary": new_summary,
            "messages": [
                RemoveMessage(id=message.id) for message in old
            ],
        }

    def agent(state: AgentState, runtime: Runtime[UserContext]):
        summary = state.get("summary", "")
        budget = max(
            1, CONTEXT_MAX_TOKENS - estimate_tokens(summary)
        )
        messages = trim_messages(state["messages"], budget)
        system_prompt = SYSTEM_PROMPT
        context = getattr(runtime, "context", None)
        user_id = getattr(context, "user_id", "")
        store = getattr(runtime, "store", None)
        profile = load_profile(store, user_id) if store and user_id else ""
        if profile:
            system_prompt = (
                f"{system_prompt}\n\n用户长期画像"
                f"(仅作参考,不要编造):\n{profile}"
            )
        if summary:
            system_prompt = (
                f"{system_prompt}\n\n较早对话的摘要"
                f"(可能不完整,仅供参考):\n{summary}"
            )
        prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt), MessagesPlaceholder("messages")]
        )
        response = (prompt | llm).invoke({"messages": messages})
        return {"messages": [response]}

    tools_node = ToolNode(
        tools,
        wrap_tool_call=security_wrapper,
        awrap_tool_call=asecurity_wrapper,
    )
    builder = StateGraph(AgentState, context_schema=UserContext)
    builder.add_node("compact", compact)
    builder.add_node("agent", agent)
    builder.add_node("tools", tools_node)
    builder.add_edge(START, "compact")
    builder.add_edge("compact", "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "compact")
    return builder.compile(checkpointer=checkpointer, store=store)


def build_simple_graph(model, tools, checkpointer=None, store=None):
    """LangChain 1.x 高层写法:create_agent 内部同样运行在 LangGraph 上。"""
    ensure_tools_allowed(tools)
    return create_agent(
        model,
        tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
        context_schema=UserContext,
        store=store,
    )
