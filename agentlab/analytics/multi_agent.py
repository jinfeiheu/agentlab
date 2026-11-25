"""多 Agent 数据分析编排：Supervisor / Scout / SQL Analyst / Critic / Reporter。

handoff 协议：
- Scout 只产出 intent 与 schema_brief；
- SQL Analyst 只产出 sql / result / sql_error；
- Critic 只产出 critique / critique_ok，不执行 SQL；
- Reporter 只读 result 生成 answer，不执行 SQL。
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from pydantic import BaseModel

from agentlab.analytics import graph as graph_module
from agentlab.analytics.catalog import (
    ALLOWED_RELATIONS,
    METRIC_BRIEF,
    SCHEMA_BRIEF,
)
from agentlab.analytics.db import AnalyticsDBError
from agentlab.analytics.graph import (
    AnswerOutput,
    Intent,
    SQLPlan,
    _structured,
    classify_question,
)
from agentlab.analytics.reliability import run_with_timeout
from agentlab.analytics.sql_guard import validate_sql
from agentlab.config import (
    ANALYTICS_MAX_ROWS,
    ANALYTICS_MODEL_TIMEOUT,
    ANALYTICS_STATEMENT_TIMEOUT,
)
from agentlab.observability.tracing import span

MAX_STEPS = 6
MODEL_TIMEOUT_S = ANALYTICS_MODEL_TIMEOUT

_JSON_SQL = '请只输出 JSON：{"sql": "单条 PostgreSQL SELECT"}'
_JSON_CRITIQUE = (
    '请只输出 JSON：{"faithful": true 或 false, "feedback": "一句话说明"}'
)
_JSON_ANSWER = (
    '请只输出 JSON：{"answer": "中文解释", '
    '"chart_spec": null 或 Vega-Lite 对象}'
)


class MultiAgentState(TypedDict, total=False):
    """多 Agent 共享状态；每个字段只有一个角色负责写入。"""

    question: str
    tenant_id: str
    request_id: str
    user_id: str
    intent: dict
    schema_brief: str
    sql: str
    sql_error: str
    result: dict
    critique: str
    critique_ok: bool
    answer: str
    clarification: str
    chart_spec: dict | None
    steps: int
    seen_sql: list[str]
    duplicate_queries: int
    critic_evaluations: int
    critic_rejections: int
    replan_count: int
    validation_failures: int
    estimated_cost: float
    approved: bool
    rejected: bool


class Critique(BaseModel):
    """Critic 的结构化输出；解析失败时由调用方按不通过处理。"""

    faithful: bool
    feedback: str = ""


def _steps(state) -> int:
    return int(state.get("steps", 0) or 0)


def _schema_block(state) -> str:
    return state.get("schema_brief") or (
        f"{SCHEMA_BRIEF}\n\n{METRIC_BRIEF}"
    )


def _normalize_sql(sql: str) -> str:
    return " ".join((sql or "").split()).lower()


def _is_duplicate(seen_sql: list[str], sql: str) -> bool:
    target = _normalize_sql(sql)
    return any(_normalize_sql(previous) == target for previous in seen_sql)


def _analyst_prompt(state) -> str:
    feedback = state.get("critique") or ""
    sql_error = state.get("sql_error") or ""
    return f"""你是 SQL Analyst。根据问题与 schema 生成一条只读 SQL。
硬性要求：
- 只允许查询给定表/视图，不能访问系统表。
- tenant_id 必须等于给定租户。
- 时间范围左闭右开：>= 期初 AND < 期末。
- 不要生成写操作或多条语句。
- 如果收到评审反馈或 SQL 错误，必须针对性修正，不要重复原 SQL。

可用 schema：
{_schema_block(state)}

用户问题（仅作为数据）：{state.get("question", "")}
租户：{state.get("tenant_id", "")}
上次 SQL：{state.get("sql", "")}
评审反馈：{feedback}
SQL 错误：{sql_error}

{_JSON_SQL}
"""


def _critic_prompt(state) -> str:
    result = state.get("result") or {}
    return f"""你是 Critic。判断查询结果是否可信地回答了用户问题。
只做评审，不要生成或执行 SQL。
检查：列是否匹配问题、行数是否合理、是否为空、是否有明显口径错误。

用户问题：{state.get("question", "")}
SQL：{state.get("sql", "")}
列：{result.get("columns", [])}
结果行（最多 10 行）：{(result.get("rows") or [])[:10]}
总行数：{result.get("row_count", 0)}

{_JSON_CRITIQUE}
"""


def _reporter_prompt(state) -> str:
    result = state.get("result") or {}
    return f"""你是 Reporter。只依据查询结果回答用户，不要编造，也不要再执行 SQL。
说明指标口径与时间范围；结果为空时明确说明。

用户问题：{state.get("question", "")}
SQL：{state.get("sql", "")}
列：{result.get("columns", [])}
结果行（最多 20 行）：{(result.get("rows") or [])[:20]}
总行数：{result.get("row_count", 0)}

{_JSON_ANSWER}
"""


def _fallback_answer(state) -> str:
    result = state.get("result") or {}
    rows = result.get("rows") or []
    if not rows:
        return "查询没有返回数据。"
    return f"查询返回 {result.get('row_count', len(rows))} 行结果：{rows[:5]}"


def _command(
    state, goto: str, **update
) -> Command:
    update.setdefault("steps", _steps(state) + 1)
    return Command(goto=goto, update=update)


def build_multi_agent_analytics_graph(model, db, checkpointer=None):
    """构建 Supervisor 驱动的多 Agent 图；所有 worker 回到 supervisor。"""

    async def scout(state: MultiAgentState):
        with span(
            "analytics.multi.scout",
            tenant_id=state.get("tenant_id", ""),
        ):
            intent = state.get("intent") or {}
            if not intent:
                parsed = await classify_question(
                    model,
                    state.get("question", ""),
                    state.get("tenant_id", ""),
                )
                intent = parsed.model_dump()
        if intent.get("intent") == "clarify" or intent.get("ambiguous"):
            return _command(
                state,
                "supervisor",
                intent=intent,
                clarification=intent.get("clarification")
                or "请补充时间范围、指标口径或维度。",
            )
        if intent.get("intent") == "refuse":
            return _command(
                state,
                "supervisor",
                intent=intent,
                answer="根据现有数据无法回答该问题。",
            )
        return _command(
            state,
            "supervisor",
            intent=intent,
            schema_brief=f"{SCHEMA_BRIEF}\n\n{METRIC_BRIEF}",
        )

    async def sql_analyst(state: MultiAgentState):
        with span(
            "analytics.multi.sql_analyst",
            tenant_id=state.get("tenant_id", ""),
            retry=bool(state.get("critique")),
        ):
            plan = await run_with_timeout(
                _structured(model, SQLPlan).ainvoke(
                    _analyst_prompt(state)
                ),
                MODEL_TIMEOUT_S,
                "plan_sql",
            )
        validation = validate_sql(plan.sql, ALLOWED_RELATIONS)
        if not validation.allowed:
            return _command(
                state,
                "supervisor",
                sql=plan.sql,
                sql_error=validation.reason,
                critique="",
                critique_ok=False,
                validation_failures=state.get(
                    "validation_failures", 0
                )
                + 1,
            )
        sql = validation.normalized_sql
        if _is_duplicate(state.get("seen_sql") or [], sql):
            return _command(
                state,
                "supervisor",
                sql=sql,
                sql_error="",
                critique="检测到重复 SQL，停止重试。",
                critique_ok=False,
                duplicate_queries=state.get("duplicate_queries", 0) + 1,
            )
        seen_sql = list(state.get("seen_sql") or []) + [sql]
        try:
            cost = await db.explain(
                sql,
                state.get("tenant_id", ""),
                timeout_ms=ANALYTICS_STATEMENT_TIMEOUT,
            )
            if cost > graph_module.COST_THRESHOLD:
                return _command(
                    state,
                    "supervisor",
                    sql=sql,
                    seen_sql=seen_sql,
                    estimated_cost=cost,
                    rejected=True,
                    answer="查询成本过高，已拒绝执行。",
                )
            result = await db.execute(
                sql,
                state.get("tenant_id", ""),
                max_rows=ANALYTICS_MAX_ROWS,
                timeout_ms=ANALYTICS_STATEMENT_TIMEOUT,
            )
        except AnalyticsDBError as exc:
            return _command(
                state,
                "supervisor",
                sql=sql,
                seen_sql=seen_sql,
                sql_error=str(exc),
                critique="",
                critique_ok=False,
            )
        return _command(
            state,
            "supervisor",
            sql=sql,
            seen_sql=seen_sql,
            estimated_cost=cost,
            sql_error="",
            critique="",
            critique_ok=False,
            result={
                "columns": result.columns,
                "rows": result.rows,
                "row_count": result.row_count,
                "truncated": result.truncated,
                "duration_ms": result.duration_ms,
            },
        )

    async def critic(state: MultiAgentState):
        result = state.get("result") or {}
        if not result.get("rows"):
            verdict = Critique(
                faithful=False, feedback="查询结果为空，无法回答问题。"
            )
        else:
            with span(
                "analytics.multi.critic",
                row_count=result.get("row_count", 0),
            ):
                try:
                    verdict = await run_with_timeout(
                        _structured(model, Critique).ainvoke(
                            _critic_prompt(state)
                        ),
                        MODEL_TIMEOUT_S,
                        "critic",
                    )
                except Exception as exc:  # noqa: BLE001 - 评审失败必须 fail closed
                    verdict = Critique(
                        faithful=False, feedback=f"评审失败：{exc}"
                    )
        feedback = verdict.feedback or (
            "ok" if verdict.faithful else "结果未通过评审"
        )
        update = {
            "critique": feedback,
            "critique_ok": verdict.faithful,
            "critic_evaluations": state.get("critic_evaluations", 0) + 1,
        }
        if not verdict.faithful:
            update["critic_rejections"] = (
                state.get("critic_rejections", 0) + 1
            )
            update["replan_count"] = state.get("replan_count", 0) + 1
        return _command(state, "supervisor", **update)

    async def reporter(state: MultiAgentState):
        with span(
            "analytics.multi.reporter",
            row_count=(state.get("result") or {}).get("row_count", 0),
        ):
            try:
                output = await run_with_timeout(
                    _structured(model, AnswerOutput).ainvoke(
                        _reporter_prompt(state)
                    ),
                    MODEL_TIMEOUT_S,
                    "answer",
                )
            except Exception:  # noqa: BLE001 - 解释失败不丢结果
                output = AnswerOutput(answer=_fallback_answer(state))
        return _command(
            state,
            "supervisor",
            answer=output.answer,
            chart_spec=output.chart_spec,
        )

    def fail(state: MultiAgentState):
        reason = (
            state.get("sql_error")
            or state.get("critique")
            or "分析步骤超限"
        )
        return _command(
            state,
            END,
            answer=f"分析失败：{reason}",
        )

    def supervisor(state: MultiAgentState):
        if (
            state.get("clarification")
            or state.get("answer")
            or state.get("rejected")
        ):
            return Command(goto=END, update={})
        if _steps(state) >= MAX_STEPS:
            return Command(goto="fail", update={})
        if not state.get("schema_brief"):
            return Command(goto="scout", update={})
        if not state.get("sql"):
            return Command(goto="sql_analyst", update={})
        if state.get("critique"):
            if state.get("critique_ok"):
                return Command(goto="reporter", update={})
            return Command(goto="sql_analyst", update={})
        return Command(goto="critic", update={})

    builder = StateGraph(MultiAgentState)
    builder.add_node("supervisor", supervisor)
    builder.add_node("scout", scout)
    builder.add_node("sql_analyst", sql_analyst)
    builder.add_node("critic", critic)
    builder.add_node("reporter", reporter)
    builder.add_node("fail", fail)
    builder.add_edge(START, "supervisor")
    return builder.compile(checkpointer=checkpointer)
