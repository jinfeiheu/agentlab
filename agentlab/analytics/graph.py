"""Analytics Agent 的显式工作流。

流程：理解 → 澄清/拒答 → 生成 SQL → 校验 → 执行 → 修复 → 回答。
"""

import logging
import time
import uuid
from typing import Literal, TypedDict

from langgraph.config import get_config
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from agentlab.analytics.audit import write_audit
from agentlab.analytics.catalog import (
    ALLOWED_RELATIONS,
    METRIC_BRIEF,
    SCHEMA_BRIEF,
)
from agentlab.analytics.db import AnalyticsDBError
from agentlab.analytics.reliability import run_with_timeout
from agentlab.analytics.sql_guard import validate_sql
from agentlab.analytics.versioning import (
    BudgetExceeded,
    CostBudget,
    PromptRegistry,
)
from agentlab.config import (
    ANALYTICS_COST_THRESHOLD,
    ANALYTICS_MAX_ROWS,
    ANALYTICS_MODEL_TIMEOUT,
    ANALYTICS_STATEMENT_TIMEOUT,
)
from agentlab.observability.metrics import AnalyticsMetrics
from agentlab.observability.tracing import span

MAX_REPAIRS = 2
MODEL_TIMEOUT_S = ANALYTICS_MODEL_TIMEOUT
COST_THRESHOLD = ANALYTICS_COST_THRESHOLD
logger = logging.getLogger(__name__)

_JSON_INTENT = (
    '请只输出 JSON：{"intent": "answer|clarify|refuse", '
    '"metrics": [], "dimensions": [], "time_range": "", '
    '"ambiguous": false, "clarification": ""}'
)
_JSON_SQL = '请只输出 JSON：{"sql": "单条 PostgreSQL SELECT"}'
_JSON_ANSWER = (
    '请只输出 JSON：{"answer": "中文解释", '
    '"chart_spec": null 或 Vega-Lite 对象}'
)

_REFUSAL_MARKERS = ("无法回答", "无法查询", "不能提供", "无法提供")


class AnalyticsState(TypedDict, total=False):
    """图的共享状态；字段按节点逐步填充。"""

    question: str
    tenant_id: str
    request_id: str
    user_id: str
    intent: dict
    clarification: str
    sql: str
    sql_error: str
    repair_count: int
    validation_failures: int
    estimated_cost: float
    approved: bool
    rejected: bool
    result: dict
    answer: str
    chart_spec: dict | None
    prompt_versions: dict[str, str]
    model_ids: dict[str, str]
    budget_spent: float
    budget_exceeded: bool


class Intent(BaseModel):
    """understand 节点的结构化输出。"""

    intent: Literal["answer", "clarify", "refuse"] = "answer"
    metrics: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    time_range: str = ""
    ambiguous: bool = False
    clarification: str = ""


class SQLPlan(BaseModel):
    """plan_sql / repair 节点的结构化输出。"""

    sql: str


class AnswerOutput(BaseModel):
    """answer 节点的结构化输出。"""

    answer: str
    chart_spec: dict | None = None


_DEFAULT_PROMPTS: PromptRegistry | None = None


def default_prompt_registry() -> PromptRegistry:
    """进程级默认 registry；测试可注入临时目录或 override。"""
    global _DEFAULT_PROMPTS
    if _DEFAULT_PROMPTS is None:
        _DEFAULT_PROMPTS = PromptRegistry()
    return _DEFAULT_PROMPTS


def _summarize(mapping: dict | None) -> str | None:
    if not mapping:
        return None
    return ",".join(
        f"{key}={value}" for key, value in sorted(mapping.items())
    )


def _after_understand(state: AnalyticsState) -> str:
    intent = state.get("intent") or {}
    if intent.get("intent") == "clarify" or intent.get("ambiguous"):
        return "clarify"
    if intent.get("intent") == "refuse":
        return "refuse"
    return "plan_sql"


def _after_validate(state: AnalyticsState) -> str:
    if not state.get("sql_error"):
        return "estimate_cost"
    return "fail" if state.get("repair_count", 0) >= MAX_REPAIRS else "repair"


def _after_estimate(state: AnalyticsState) -> str:
    if not state.get("sql_error"):
        return "approve"
    return "fail" if state.get("repair_count", 0) >= MAX_REPAIRS else "repair"


def _after_approve(state: AnalyticsState) -> str:
    return "execute" if state.get("approved") else "reject"


def _after_execute(state: AnalyticsState) -> str:
    if not state.get("sql_error"):
        return "answer"
    return "fail" if state.get("repair_count", 0) >= MAX_REPAIRS else "repair"


def _structured(model, schema):
    """DeepSeek thinking mode 不支持 tool_choice，统一用 json_mode。"""
    return model.with_structured_output(schema, method="json_mode")


async def classify_question(
    model,
    question: str,
    tenant_id: str,
    config=None,
    prompt_registry: PromptRegistry | None = None,
) -> Intent:
    """独立意图解析；auto 路由与图内 understand 共用。"""
    registry = prompt_registry or default_prompt_registry()
    prompt = registry.render(
        "understand",
        schema_brief=SCHEMA_BRIEF,
        metric_brief=METRIC_BRIEF,
        question=question,
        tenant_id=tenant_id,
        json_intent=_JSON_INTENT,
    )
    return await run_with_timeout(
        _structured(model, Intent).ainvoke(prompt, config=config or {}),
        MODEL_TIMEOUT_S,
        "understand",
    )


def build_analytics_graph(
    model,
    db,
    checkpointer=None,
    prompt_registry: PromptRegistry | None = None,
    model_router=None,
    budget: CostBudget | None = None,
):
    """构建单 Agent 基线图；模型、prompt registry 和预算都可注入。"""
    registry = prompt_registry or default_prompt_registry()
    budget = budget or CostBudget()

    def _record(state: AnalyticsState, spec) -> dict:
        versions = dict(state.get("prompt_versions") or {})
        versions[spec.prompt_id] = spec.version
        models = dict(state.get("model_ids") or {})
        models[spec.prompt_id] = spec.model
        return {"prompt_versions": versions, "model_ids": models}

    async def _invoke(prompt_id, schema, state, variables, label):
        spec = registry.get(prompt_id)
        text = registry.render(prompt_id, **variables)
        spent = budget.charge(
            float(state.get("budget_spent", 0.0) or 0.0)
        )
        node_model = model_router(spec.model) if model_router else model
        with span(
            "analytics.model",
            prompt_id=spec.prompt_id,
            prompt_version=spec.version,
            model_id=spec.model,
        ):
            result = await run_with_timeout(
                _structured(node_model, schema).ainvoke(text),
                MODEL_TIMEOUT_S,
                label,
            )
        meta = _record(state, spec)
        meta["budget_spent"] = spent
        return result, meta

    async def understand(state: AnalyticsState):
        if state.get("intent"):
            # auto 路由已经做过意图解析，避免重复模型调用。
            spec = registry.get("understand")
            return {"intent": state["intent"], **_record(state, spec)}
        with span(
            "analytics.understand",
            tenant_id=state.get("tenant_id", ""),
            question_chars=len(state.get("question", "")),
        ):
            result, meta = await _invoke(
                "understand",
                Intent,
                state,
                {
                    "schema_brief": SCHEMA_BRIEF,
                    "metric_brief": METRIC_BRIEF,
                    "question": state.get("question", ""),
                    "tenant_id": state.get("tenant_id", ""),
                    "json_intent": _JSON_INTENT,
                },
                "understand",
            )
        return {"intent": result.model_dump(), **meta}

    def clarify(state: AnalyticsState):
        intent = state.get("intent") or {}
        return {
            "clarification": intent.get("clarification")
            or "请补充时间范围、指标口径或维度。"
        }

    def refuse(state: AnalyticsState):
        return {"answer": "根据现有数据无法回答该问题。", "clarification": ""}

    async def plan_sql(state: AnalyticsState):
        with span(
            "analytics.plan_sql",
            tenant_id=state.get("tenant_id", ""),
        ):
            plan, meta = await _invoke(
                "plan_sql",
                SQLPlan,
                state,
                {
                    "schema_brief": SCHEMA_BRIEF,
                    "metric_brief": METRIC_BRIEF,
                    "question": state.get("question", ""),
                    "intent": state.get("intent") or {},
                    "tenant_id": state.get("tenant_id", ""),
                    "json_sql": _JSON_SQL,
                },
                "plan_sql",
            )
        return {"sql": plan.sql, "sql_error": "", **meta}

    def validate_sql_node(state: AnalyticsState):
        with span(
            "analytics.validate_sql",
            tenant_id=state.get("tenant_id", ""),
        ):
            validation = validate_sql(
                state.get("sql", ""), ALLOWED_RELATIONS
            )
            if not validation.allowed:
                return {
                    "sql_error": validation.reason,
                    "validation_failures": state.get(
                        "validation_failures", 0
                    )
                    + 1,
                }
        return {"sql": validation.normalized_sql, "sql_error": ""}

    async def estimate_cost(state: AnalyticsState):
        with span(
            "analytics.estimate_cost",
            tenant_id=state.get("tenant_id", ""),
        ):
            try:
                cost = await db.explain(
                    state.get("sql", ""),
                    state.get("tenant_id", ""),
                    timeout_ms=ANALYTICS_STATEMENT_TIMEOUT,
                )
            except AnalyticsDBError as exc:
                return {"sql_error": str(exc)}
        return {"estimated_cost": cost, "sql_error": ""}

    def approve(state: AnalyticsState):
        cost = float(state.get("estimated_cost", 0.0) or 0.0)
        with span("analytics.approve", estimated_cost=cost):
            if cost <= COST_THRESHOLD:
                return {"approved": True, "rejected": False}
            configurable = (get_config() or {}).get("configurable") or {}
            if not configurable.get("thread_id"):
                # 没有 checkpointer/thread 时 interrupt 无法恢复，必须 fail closed。
                return {
                    "approved": False,
                    "rejected": True,
                    "answer": "查询成本过高，需要人工审批后执行。",
                }
            decision = interrupt(
                {
                    "question": "查询预估成本较高，是否继续执行？",
                    "sql": state.get("sql", ""),
                    "estimated_cost": cost,
                    "threshold": COST_THRESHOLD,
                }
            )
        approved = str(decision).strip().lower() in {
            "y",
            "yes",
            "approve",
            "同意",
            "批准",
        }
        if not approved:
            return {
                "approved": False,
                "rejected": True,
                "answer": "查询成本过高，已拒绝执行。",
            }
        return {"approved": True, "rejected": False}

    async def execute(state: AnalyticsState):
        with span(
            "analytics.execute",
            tenant_id=state.get("tenant_id", ""),
            sql_chars=len(state.get("sql", "")),
        ):
            try:
                result = await db.execute(
                    state.get("sql", ""),
                    state.get("tenant_id", ""),
                    max_rows=ANALYTICS_MAX_ROWS,
                    timeout_ms=ANALYTICS_STATEMENT_TIMEOUT,
                )
            except AnalyticsDBError as exc:
                return {"sql_error": str(exc)}
        return {
            "result": {
                "columns": result.columns,
                "rows": result.rows,
                "row_count": result.row_count,
                "truncated": result.truncated,
                "duration_ms": result.duration_ms,
            },
            "sql_error": "",
        }

    async def repair(state: AnalyticsState):
        with span(
            "analytics.repair",
            repair_count=state.get("repair_count", 0),
        ):
            plan, meta = await _invoke(
                "repair",
                SQLPlan,
                state,
                {
                    "question": state.get("question", ""),
                    "sql": state.get("sql", ""),
                    "sql_error": state.get("sql_error", ""),
                    "schema_brief": SCHEMA_BRIEF,
                    "metric_brief": METRIC_BRIEF,
                    "json_sql": _JSON_SQL,
                },
                "repair",
            )
        return {
            "sql": plan.sql,
            "sql_error": "",
            "repair_count": state.get("repair_count", 0) + 1,
            **meta,
        }

    def fail(state: AnalyticsState):
        return {
            "answer": f"SQL 修复失败：{state.get('sql_error') or '未知错误'}"
        }

    async def answer(state: AnalyticsState):
        result = state.get("result") or {}
        rows = result.get("rows") or []
        variables = {
            "question": state.get("question", ""),
            "sql": state.get("sql", ""),
            "columns": result.get("columns", []),
            "rows": rows[:20],
            "row_count": result.get("row_count", 0),
            "truncated": result.get("truncated", False),
            "json_answer": _JSON_ANSWER,
        }
        with span(
            "analytics.answer",
            row_count=result.get("row_count", 0),
        ):
            try:
                output, meta = await _invoke(
                    "answer", AnswerOutput, state, variables, "answer"
                )
            except BudgetExceeded:
                raise
            except Exception as exc:  # noqa: BLE001 - 解析失败不能丢结果
                logger.warning(
                    "analytics_answer_failed error=%s",
                    type(exc).__name__,
                )
                text = (
                    "查询没有返回数据。"
                    if not rows
                    else f"查询返回 {result.get('row_count', len(rows))} "
                    f"行结果：{rows[:5]}"
                )
                output = AnswerOutput(answer=text, chart_spec=None)
                meta = _record(state, registry.get("answer"))
        return {
            "answer": output.answer,
            "chart_spec": output.chart_spec,
            **meta,
        }

    builder = StateGraph(AnalyticsState)
    builder.add_node("understand", understand)
    builder.add_node("clarify", clarify)
    builder.add_node("refuse", refuse)
    builder.add_node("plan_sql", plan_sql)
    builder.add_node("validate_sql", validate_sql_node)
    builder.add_node("estimate_cost", estimate_cost)
    builder.add_node("approve", approve)
    builder.add_node("execute", execute)
    builder.add_node("repair", repair)
    builder.add_node("answer", answer)
    builder.add_node("fail", fail)

    builder.add_edge(START, "understand")
    builder.add_conditional_edges(
        "understand",
        _after_understand,
        {"clarify": "clarify", "refuse": "refuse", "plan_sql": "plan_sql"},
    )
    builder.add_edge("clarify", END)
    builder.add_edge("refuse", END)
    builder.add_edge("plan_sql", "validate_sql")
    builder.add_conditional_edges(
        "validate_sql",
        _after_validate,
        {
            "estimate_cost": "estimate_cost",
            "repair": "repair",
            "fail": "fail",
        },
    )
    builder.add_conditional_edges(
        "estimate_cost",
        _after_estimate,
        {"approve": "approve", "repair": "repair", "fail": "fail"},
    )
    builder.add_conditional_edges(
        "approve",
        _after_approve,
        {"execute": "execute", "reject": END},
    )
    builder.add_edge("repair", "validate_sql")
    builder.add_conditional_edges(
        "execute",
        _after_execute,
        {"answer": "answer", "repair": "repair", "fail": "fail"},
    )
    builder.add_edge("answer", END)
    builder.add_edge("fail", END)
    return builder.compile(checkpointer=checkpointer)


def _audit_status(state: AnalyticsState) -> str:
    if state.get("rejected"):
        return "rejected"
    if state.get("clarification"):
        return "clarify"
    if state.get("result"):
        return "success"
    answer = state.get("answer") or ""
    if any(marker in answer for marker in _REFUSAL_MARKERS):
        return "refuse"
    return "error"


async def run_analytics_question(
    graph,
    question: str,
    tenant_id: str,
    config=None,
    user_id: str = "anonymous",
    metrics: AnalyticsMetrics | None = None,
) -> dict:
    """执行一轮问答，写审计，记录日志和过程指标。"""
    request_id = uuid.uuid4().hex
    started = time.perf_counter()
    payload = {
        "question": question,
        "tenant_id": tenant_id,
        "request_id": request_id,
        "user_id": user_id,
        "intent": {},
        "clarification": "",
        "sql": "",
        "sql_error": "",
        "repair_count": 0,
        "validation_failures": 0,
        "estimated_cost": 0.0,
        "approved": False,
        "rejected": False,
        "result": {},
        "answer": "",
        "chart_spec": None,
        "prompt_versions": {},
        "model_ids": {},
        "budget_spent": 0.0,
        "budget_exceeded": False,
    }
    try:
        state = await graph.ainvoke(payload, config or {})
    except BudgetExceeded as exc:
        duration_ms = (time.perf_counter() - started) * 1000
        await write_audit(
            request_id=request_id,
            user_id=user_id,
            tenant_id=tenant_id,
            question=question,
            sql="",
            status="budget",
            row_count=0,
            estimated_cost=0.0,
            duration_ms=duration_ms,
        )
        logger.warning(
            "analytics_query request_id=%s tenant_id=%s "
            "status=budget duration_ms=%.1f",
            request_id,
            tenant_id,
            duration_ms,
        )
        if metrics is not None:
            metrics.record(
                status="budget",
                latency_ms=duration_ms,
                row_count=0,
                cost=0.0,
            )
        return {
            **payload,
            "request_id": request_id,
            "user_id": user_id,
            "answer": str(exc),
            "budget_exceeded": True,
        }
    except Exception:
        duration_ms = (time.perf_counter() - started) * 1000
        await write_audit(
            request_id=request_id,
            user_id=user_id,
            tenant_id=tenant_id,
            question=question,
            sql="",
            status="error",
            row_count=0,
            estimated_cost=0.0,
            duration_ms=duration_ms,
        )
        logger.warning(
            "analytics_query request_id=%s tenant_id=%s "
            "status=error duration_ms=%.1f",
            request_id,
            tenant_id,
            duration_ms,
        )
        if metrics is not None:
            metrics.record(
                status="error",
                latency_ms=duration_ms,
                row_count=0,
                cost=0.0,
            )
        raise

    duration_ms = (time.perf_counter() - started) * 1000
    result = state.get("result") or {}
    status = _audit_status(state)
    await write_audit(
        request_id=request_id,
        user_id=user_id,
        tenant_id=tenant_id,
        question=question,
        sql=state.get("sql", ""),
        status=status,
        row_count=result.get("row_count", 0),
        estimated_cost=state.get("estimated_cost", 0.0),
        duration_ms=duration_ms,
        prompt_version=_summarize(state.get("prompt_versions")),
        model_id=_summarize(state.get("model_ids")),
    )
    logger.info(
        "analytics_query request_id=%s tenant_id=%s status=%s "
        "row_count=%s duration_ms=%.1f",
        request_id,
        tenant_id,
        status,
        result.get("row_count", 0),
        duration_ms,
    )
    if metrics is not None:
        sql_error = (state.get("sql_error") or "").lower()
        metrics.record(
            status=status,
            latency_ms=duration_ms,
            row_count=result.get("row_count", 0),
            cost=float(state.get("estimated_cost", 0.0) or 0.0),
            permission_denied="permission denied" in sql_error,
            clarification=bool(state.get("clarification")),
            repair_count=state.get("repair_count", 0),
        )
    state["request_id"] = request_id
    state["user_id"] = user_id
    return state
