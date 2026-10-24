"""单 Agent 图构建:手写 StateGraph 与 create_agent 两种写法。"""

from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from auth import UserContext
from security import asecurity_wrapper, ensure_tools_allowed, security_wrapper

SYSTEM_PROMPT = """你是一个中文技术问答助手,回答要简洁、准确。

工具使用规则:
1. 回答 LangChain、LangGraph、RAG、Agent 等技术问题时,先调用 search_docs 检索本地知识库。
2. 只依据检索到的片段回答,不要用片段之外的知识补充事实;片段不足以回答时,直接说“根据现有资料无法回答”。
3. 引用时在句末标注来源,格式为 [来源:文件名#章节]。
4. 需要算术时调用 calculator,不要心算。
5. 用户要求发送报告时,把要发送的内容传给 send_report;该工具会请求人工确认。
6. 查询工单时调用 get_ticket;只能查询当前用户自己的工单,不要猜测其他用户的数据。
"""


def build_graph(model, tools, checkpointer=None, store=None):
    """手写 LangGraph:agent 与 tools 循环,直到模型不再调用工具。"""
    ensure_tools_allowed(tools)
    llm = model.bind_tools(tools)
    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), MessagesPlaceholder("messages")]
    )

    def agent(state: MessagesState):
        response = (prompt | llm).invoke({"messages": state["messages"]})
        return {"messages": [response]}

    tools_node = ToolNode(
        tools,
        wrap_tool_call=security_wrapper,
        awrap_tool_call=asecurity_wrapper,
    )
    builder = StateGraph(MessagesState, context_schema=UserContext)
    builder.add_node("agent", agent)
    builder.add_node("tools", tools_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")
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
