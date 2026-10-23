"""三个工具:安全计算器、知识库检索、发送报告(人工确认)。"""

import ast
import operator

from langchain_core.tools import BaseTool, tool
from langgraph.types import interrupt

from rag import format_docs

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_MAX_EXPRESSION_LENGTH = 100
_MAX_EXPONENT = 1000
# 约 4215 位十进制数,低于 Python 默认的 4300 位整数转字符串上限。
_MAX_RESULT_BITS = 14_000
_CONFIRM_WORDS = {"y", "yes", "是", "确认", "ok"}


def _eval_ast(node: ast.AST) -> int | float:
    """只对数字、括号和四则运算求值,绝不执行任意代码。"""
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    ):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left = _eval_ast(node.left)
        right = _eval_ast(node.right)
        if isinstance(node.op, ast.Pow):
            if abs(right) > _MAX_EXPONENT:
                raise ValueError("指数过大")
            # 先估算幂结果的位数,避免 ((9**999)**999)**999 这类嵌套指数把内存吃光。
            if (
                isinstance(left, int)
                and isinstance(right, int)
                and right > 0
                and abs(left) > 1
                and left.bit_length() * right > _MAX_RESULT_BITS
            ):
                raise ValueError("结果过大")
        result = _OPS[type(node.op)](left, right)
        # 乘法/加法等也可能把中间结果滚大,统一兜底。
        if isinstance(result, int) and result.bit_length() > _MAX_RESULT_BITS:
            raise ValueError("结果过大")
        return result
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_ast(node.operand))
    raise ValueError("只支持数字、括号和 + - * / // % ** 运算")


@tool
def calculator(expression: str) -> str:
    """计算数学表达式,支持 + - * / // % ** 和括号。"""
    if len(expression) > _MAX_EXPRESSION_LENGTH:
        return "错误:表达式太长"
    try:
        return str(_eval_ast(ast.parse(expression, mode="eval")))
    except ZeroDivisionError:
        return "错误:除数不能为 0"
    except Exception as exc:
        return f"错误:{exc}"


def make_search_tool(retriever, reranker=None, top_n: int = 3) -> BaseTool:
    """把 retriever 封装成 agent 可调用的检索工具。"""

    @tool
    def search_docs(query: str) -> str:
        """从本地知识库检索 LangChain/LangGraph 相关资料。"""
        docs = retriever.invoke(query)
        if reranker is not None:
            docs = reranker.rerank(query, docs)
        docs = list(docs)[:top_n]
        if not docs:
            return "知识库中没有找到相关内容。"
        return format_docs(docs)

    return search_docs


@tool
def send_report(content: str) -> str:
    """把一段内容作为报告发送给用户(模拟发送,发送前需人工确认)。"""
    answer = interrupt({"question": "确认发送这份报告吗?", "content": content})
    if str(answer).strip().lower() in _CONFIRM_WORDS:
        return f"已发送(模拟):{content}"
    return "已取消发送。"
