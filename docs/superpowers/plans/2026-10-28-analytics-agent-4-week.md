# 企业数据分析 Agent 4 周实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 `langchain-demo` 上做一个生产级数据分析 Agent 参考切片：自然语言 → 安全 SQL → 执行 → 修复 → 解释/图表 → 审计，并用 50 条 golden 任务验证。

**Architecture:** 新增 `agentlab/analytics/` 子包，使用 LangGraph 显式节点：understand → clarify → plan_sql → validate_sql → approve → execute → repair → answer → audit。Postgres `analytics` schema 承载合成业务数据、指标目录和审计表；只读角色 + RLS + sqlglot 守卫构成三层安全。评测以 execution accuracy 为主、LLM judge 为辅。

**Tech Stack:** Python 3.12、uv、LangGraph、FastAPI、Postgres 16、sqlglot、Faker、pytest、OpenTelemetry/Phoenix、Prometheus（Week 2+）。

**Spec:** `docs/superpowers/specs/2026-10-28-analytics-agent-design.md`

## Global Constraints

- 源码本地运行：`uv run ...`；Docker 只用于 Postgres/Redis/Prometheus 等依赖，不构建应用镜像。
- 不改变现有 RAG Agent 行为；新功能走 `agentlab/analytics/` 和独立测试。
- 所有用户可见文字、注释用中文。
- 单元测试离线可跑；需要 Postgres 的测试标记 `@pytest.mark.integration`，通过 `RUN_INTEGRATION=1` 开启。
- 只读安全：应用不使用 postgres 超级用户；SQL 守卫、只读角色、RLS 三层都必须有测试。
- 不自动 git commit；每个任务结束跑完整测试，是否提交由用户决定。
- 测试命令：`uv run pytest -q`；集成：`RUN_INTEGRATION=1 uv run pytest -q -m integration`。

## Review Focus

1. **SQL 注入与多语句**：`SELECT 1; DROP TABLE ...`、注释绕过、`COPY`、`SET`、系统表访问必须被拒绝。Task 1 测试。
2. **RLS 绕过**：用户 A 不能通过改 SQL/改 tenant 查到 B 的数据。Task 3 测试。
3. **PII 泄露**：Agent 只能查脱敏视图，结果和日志都不出现邮箱/手机号。Task 3 测试。
4. **高成本查询**：全表扫描/大范围导出不能拖垮 DB，必须 `EXPLAIN` 估算 + 超时 + HITL。Task 4 测试。
5. **歧义/不可回答**：信息不足时应澄清，数据没有时应拒答，不能硬编。Task 3 测试。
6. **评测假阳性**：execution accuracy 必须做结果归一化（顺序、数值容差、空值），不能只比字符串。Task 5 测试。
7. **计划不合法/过度规划**：环、未知工具/指标、超预算、重复步骤、无进展必须被拒绝或终止。Task 4.5 测试。
8. **并行部分失败/取消**：独立步骤并行时，一个失败不能丢全部结果；取消后不能继续启动新步骤。Task 4.6 测试。
9. **多 Agent handoff/重复工作**：角色只消费/产出约定字段，Reporter 不重复执行 SQL，重复步骤被检测。Task 5.5 测试。
10. **动态工具子集**：按角色/租户返回工具，未知工具被拒绝。Task 4.6 测试。

---

# Week 1：数据、只读 DB、SQL 守卫、基础图

### Task 1: 合成数据 + 只读连接 + SQL 守卫

**Files:**
- Create: `agentlab/analytics/__init__.py`
- Create: `agentlab/analytics/config.py`
- Create: `agentlab/analytics/catalog.py`
- Create: `agentlab/analytics/sql_guard.py`
- Create: `agentlab/analytics/db.py`
- Create: `agentlab/analytics/seed.py`
- Create: `scripts/start_analytics_db.sh`
- Modify: `agentlab/config.py`（`ANALYTICS_*` 环境变量）
- Modify: `pyproject.toml`（`sqlglot`、`faker`）
- Test: `tests/test_analytics_guard.py`、`tests/test_analytics_db.py`、`tests/test_analytics_seed.py`

**Interfaces:**
- `validate_sql(sql: str, allowed_relations: set[str]) -> ValidationResult`；`ValidationResult.allowed: bool`、`reason: str`、`normalized_sql: str`。
- `async AnalyticsDB.execute(sql: str, tenant_id: str, max_rows: int = 200, timeout_ms: int = 5000) -> QueryResult`；`QueryResult.columns: list[str]`、`rows: list[tuple]`、`row_count: int`、`truncated: bool`、`duration_ms: float`。
- `seed_analytics(reset: bool = False, scale: float = 1.0) -> None`。

- [ ] **Step 1: 写失败的 SQL 守卫测试**

```python
def test_guard_rejects_multi_statement():
    result = validate_sql("SELECT 1; DROP TABLE orders", ALLOWED)
    assert result.allowed is False


def test_guard_rejects_dml_and_ddl():
    for sql in ("DELETE FROM orders", "UPDATE orders SET status='x'", "CREATE TABLE x(id int)"):
        assert validate_sql(sql, ALLOWED).allowed is False


def test_guard_rejects_system_tables():
    assert validate_sql("SELECT * FROM pg_catalog.pg_tables", ALLOWED).allowed is False
    assert validate_sql("SELECT * FROM information_schema.tables", ALLOWED).allowed is False


def test_guard_adds_limit():
    result = validate_sql("SELECT * FROM orders", ALLOWED)
    assert result.allowed is True
    assert "LIMIT" in result.normalized_sql.upper()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest -q tests/test_analytics_guard.py`
Expected: FAIL（`agentlab.analytics.sql_guard` 不存在）。

- [ ] **Step 3: 实现 `sql_guard.py`**

用 `sqlglot.parse` 解析；要求恰好一条语句、根节点为 `exp.Select`；禁止 `exp.Insert/Update/Delete/Create/Drop/Alter/Copy/Set/Command`；遍历 `exp.Table` 校验 allowlist；拒绝 `pg_catalog`/`information_schema`；没有 `LIMIT` 时补 `LIMIT 200`。

- [ ] **Step 4: 运行守卫测试确认通过**

Run: `uv run pytest -q tests/test_analytics_guard.py`
Expected: PASS。

- [ ] **Step 5: 写失败的 DB 集成测试**

```python
@pytest.mark.integration
async def test_reader_role_cannot_write(analytics_db):
    with pytest.raises(Exception):
        await analytics_db.execute("DELETE FROM orders", tenant_id="tenant_a")


@pytest.mark.integration
async def test_execute_applies_timeout_and_limit(analytics_db):
    result = await analytics_db.execute(
        "SELECT * FROM orders", tenant_id="tenant_a", max_rows=10, timeout_ms=1000
    )
    assert result.row_count <= 10
```

- [ ] **Step 6: 实现 `db.py`**

使用 `ANALYTICS_DATABASE_URL`（只读角色），每次查询新连接；事务内 `SET LOCAL statement_timeout`、`SET LOCAL app.tenant_id`；执行后截断到 `max_rows`；返回列/行/耗时；异常统一包装成 `AnalyticsDBError`。

- [ ] **Step 7: 写失败的 seed 测试并实现 `seed.py`**

测试：`seed_analytics(reset=True)` 后表存在、行数 > 0、至少 3 个 tenant、`metric_catalog` 有 revenue/refund_rate/active_customers 等口径。

- [ ] **Step 8: 编写 `scripts/start_analytics_db.sh`**

复用现有 Postgres 容器；创建 `analytics` schema、只读角色 `analytics_reader`、表、视图、种子数据；幂等。

- [ ] **Step 9: 运行测试**

Run: `uv run pytest -q`（离线）  
Run: `RUN_INTEGRATION=1 uv run pytest -q -m integration tests/test_analytics_db.py tests/test_analytics_seed.py`
Expected: 全绿。

---

### Task 2: Analytics Graph + 20 条 Golden

**Files:**
- Create: `agentlab/analytics/graph.py`
- Create: `agentlab/analytics/tools.py`
- Create: `eval/analytics_golden.jsonl`
- Create: `eval/run_analytics_eval.py`
- Create: `docs/adr/2026-10-28-analytics-agent-architecture.md`
- Modify: `agentlab/config.py`（图/模型配置）
- Test: `tests/test_analytics_graph.py`、`tests/test_analytics_eval.py`

**Interfaces:**
- `AnalyticsState`：`question`、`tenant_id`、`intent`、`clarification`、`sql`、`sql_error`、`repair_count`、`result`、`answer`、`chart_spec`。
- `build_analytics_graph(model, db, checkpointer=None)`。
- `async run_analytics_question(graph, question, tenant_id, config) -> dict`。

- [ ] **Step 1: 写失败的图测试**

用 `FakeRunnable` 模拟 understand/plan/answer；用 `FakeAnalyticsDB` 返回固定结果。测试：
- 正常问题：生成 SQL → 守卫通过 → 执行 → 回答包含结果。
- 歧义问题：`clarification` 非空，不执行 SQL。
- 不可回答：返回拒答，不执行 SQL。
- SQL 错误：repair 一次后成功。

- [ ] **Step 2: 运行确认失败**

Run: `uv run pytest -q tests/test_analytics_graph.py`
Expected: FAIL。

- [ ] **Step 3: 实现图节点**

`understand` 用 structured output 输出 `{intent, metrics, dimensions, time_range, ambiguous, clarification}`；`plan_sql` 输出 SQL；`validate` 调用 `validate_sql`；`execute` 调用 `AnalyticsDB`；`repair` 最多 2 次；`answer` 生成中文解释 + 图表 spec。

- [ ] **Step 4: 实现 20 条 golden 与 eval runner**

`eval/analytics_golden.jsonl` 字段：`question`、`tenant_id`、`expected_result`、`expected_outcome`（answer/clarify/refuse）、`tags`。  
`eval/run_analytics_eval.py` 计算 execution_accuracy、clarification_rate、refusal_rate、cost、latency。

- [ ] **Step 5: 运行测试与 20 条评测**

Run: `uv run pytest -q`  
Run: `uv run python -m eval.run_analytics_eval --limit 20`
Expected: 全绿；记录 baseline 指标。

- [ ] **Step 6: 写架构决策记录（ADR）**

创建 `docs/adr/2026-10-28-analytics-agent-architecture.md`，比较：
- 纯 ReAct
- Plan-and-Execute + repair
- Reflexion / Critic
- Supervisor 多 Agent
- 并行 fan-out/fan-in

写明本周为什么先用显式工作流、Week 2/3 如何加入计划/验证/多 Agent，以及各自成本/延迟/失败模式。ADR 是面试时讲“为什么这么设计”的证据。

---

# Week 2：安全、审计、歧义、计划/并行、可靠性、可观测

### Task 3: RLS + 审计 + PII + 歧义

**Files:**
- Modify: `agentlab/analytics/db.py`、`seed.py`、`graph.py`
- Create: `agentlab/analytics/audit.py`
- Test: `tests/test_analytics_security.py`、`tests/test_analytics_ambiguity.py`

**Interfaces:**
- `write_audit(...) -> None`；字段见设计文档。
- `AnalyticsDB.execute` 强制 `SET LOCAL app.tenant_id`；RLS policy 在 seed 脚本中创建。

- [ ] **Step 1: 写失败的越权测试**

tenant A 的 SQL 不能返回 tenant B 行；即使 SQL 显式 `WHERE tenant_id='tenant_b'`，结果也必须为空或被拒绝。

- [ ] **Step 2: 写失败的 PII 测试**

查询 `customers_safe` 不出现邮箱/手机号；查询原始 `customers` 被 allowlist 拒绝；日志/trace 不出现 PII。

- [ ] **Step 3: 写失败的审计测试**

每次执行（成功/失败/拒绝）都写一条 `analytics_audit`；字段完整；request_id 可关联 trace。

- [ ] **Step 4: 写失败的歧义/拒答测试**

“最近收入怎么样？” → 触发 clarify；“数据里没有的指标” → 拒答，不执行 SQL。

- [ ] **Step 5: 实现并跑全量测试**

Run: `uv run pytest -q`  
Run: `RUN_INTEGRATION=1 uv run pytest -q -m integration tests/test_analytics_security.py`
Expected: 全绿。

### Task 4: 可靠性 + 可观测 + 成本守卫

**Files:**
- Create: `agentlab/analytics/reliability.py`
- Modify: `agentlab/analytics/db.py`、`graph.py`、`agentlab/observability/tracing.py`
- Test: `tests/test_analytics_reliability.py`、`tests/test_analytics_observability.py`

- [ ] **Step 1: 写失败的超时/重试/熔断测试**

DB 超时、模型超时、SQL 连续失败、repair 超限；确保不挂起、返回可读错误。

- [ ] **Step 2: 写失败的 EXPLAIN/成本守卫测试**

`EXPLAIN` 估算成本超阈值时触发 `approve` interrupt；拒绝后不执行；`statement_timeout` 生效。

- [ ] **Step 3: 实现 spans/metrics/logs**

span：`analytics.understand`、`plan_sql`、`validate_sql`、`execute`、`repair`、`answer`；指标：查询数、错误率、P50/P95、行数、成本、权限拒绝、澄清率。

- [ ] **Step 4: 运行测试**

Run: `uv run pytest -q`  
Expected: 全绿；故障注入场景不挂起。

### Task 4.5: 计划表示 + 验证/反思 + 重规划 + 计划审批

**Files:**
- Create: `agentlab/analytics/planning.py`
- Create: `agentlab/analytics/verification.py`
- Modify: `agentlab/analytics/graph.py`
- Test: `tests/test_analytics_planning.py`、`tests/test_analytics_verification.py`

**Interfaces:**
- `PlanStep(id, goal, kind, depends_on, metric_ids, expected_output, status, result_ref)`。
- `AnalyticsPlan(question, steps, assumptions, clarification_needed, max_steps, version)`。
- `plan_question(model, question, catalog) -> AnalyticsPlan`。
- `validate_plan(plan, allowed_tools, allowed_metrics, budget) -> PlanValidation`。
- `verify_step(step, result) -> StepVerdict`；`classify_failure(error, result) -> FailureClass`。
- `MAX_REPLANS=2`；`max_steps` 默认 6。

- [ ] **Step 1: 写失败的计划测试**

简单问题 → 1 步；多指标/多跳问题 → 多步且依赖正确；拒绝环、未知指标、未知工具、超预算；计划审批：步骤数/预估成本超阈值触发 `interrupt`，用户可批准/编辑/拒绝。

- [ ] **Step 2: 运行确认失败**

Run: `uv run pytest -q tests/test_analytics_planning.py`
Expected: FAIL。

- [ ] **Step 3: 实现 `planning.py`**

`plan_question` 用 structured output 输出步骤列表；`validate_plan` 检查 DAG/allowlist/预算/每步 `expected_output`；计划写入 state 并落 checkpoint。

- [ ] **Step 4: 写失败的验证/重规划测试**

空结果、行数过大、列缺失、指标口径冲突、结果异常值分别被分类；`replan` 只重排未完成步骤；无进展/重复步骤/超预算终止。

- [ ] **Step 5: 实现 `verification.py` 与重规划节点**

每步验收 + 最终验收；失败分类 → repair/replan/clarify/refuse；最多 2 次重规划；记录 `failure_class` 与 `replan_count`。

- [ ] **Step 6: 运行测试**

Run: `uv run pytest -q`
Expected: 全绿。

### Task 4.6: 并行执行 + Skill 注册 + 预算/取消

**Files:**
- Create: `agentlab/analytics/executor.py`
- Create: `agentlab/analytics/registry.py`
- Create: `agentlab/analytics/budget.py`
- Modify: `agentlab/analytics/graph.py`、`tools.py`
- Test: `tests/test_analytics_executor.py`、`tests/test_analytics_registry.py`、`tests/test_analytics_budget.py`

**Interfaces:**
- `SkillSpec(name, description, input_schema, output_schema, permissions, cost_hint, latency_hint, roles)`。
- `skills_for(user, question) -> list[SkillSpec]`。
- `execute_plan(plan, db, budget, max_concurrency=3) -> PlanResult`；独立步骤用 `Send` 并行。
- `Budget(max_steps, max_tokens, max_cost, deadline_s, max_concurrency)`；`consume()`、`exhausted()`。
- `cancel_task(request_id)`；取消传播到子步骤。

- [ ] **Step 1: 写失败的并行测试**

两个独立指标查询并行执行（fake async 延迟证明重叠）；有依赖的步骤串行；部分失败返回部分结果 + 明确错误；超过 `max_concurrency` 排队。

- [ ] **Step 2: 写失败的注册/预算/取消测试**

按角色/租户返回工具子集；未知工具拒绝；步骤/token/成本/时间超限终止；取消后不再启动新步骤，已执行步骤保留审计。

- [ ] **Step 3: 实现 executor/registry/budget**

fan-out/fan-in、去重、部分失败降级；`SkillSpec` 注册与动态子集；`Budget` 每个节点扣减；取消信号检查。

- [ ] **Step 4: 运行测试**

Run: `uv run pytest -q`
Expected: 全绿。

---

# Week 3：50 条评测、CI 门禁、多 Agent、成本/版本

### Task 5: 50 条 Golden + Eval Runner + CI

**Files:**
- Modify: `eval/analytics_golden.jsonl`、`eval/run_analytics_eval.py`
- Create: `scripts/ci_analytics.sh` 或 `.github/workflows/analytics-eval.yml`
- Test: `tests/test_analytics_eval.py`

- [ ] **Step 1: 写失败的结果归一化测试**

顺序不同、数值容差、空值、重复行、浮点误差不应误判；字符串比较必须失败。

- [ ] **Step 2: 扩充到 50 条**

40 可回答 / 5 歧义 / 5 不可回答；覆盖 join、聚合、窗口、时间、退款、权限、PII、昂贵查询。

- [ ] **Step 3: CI 门禁**

单测 + 20 条 smoke eval；阈值：task_success 回退 >3% 失败；permission_violation >0 失败；PII 泄露失败。

- [ ] **Step 4: 跑完整评测并记录 baseline**

Run: `uv run python -m eval.run_analytics_eval --limit 50`
Expected: 指标报告 + badcase 列表。

- [ ] **Step 5: 增加轨迹/过程指标与失败分类**

`eval/run_analytics_eval.py` 增加：
- plan_validity、step_count、unnecessary_steps
- tool_selection_accuracy
- replan_success、route_accuracy、critic_catch_rate
- failure_class 统计：ambiguation/schema_gap/metric_conflict/sql_error/empty_result/permission/cost/model_error/tool_error
- 每类恢复率；badcase 输出可回流 golden 的 JSON。

- [ ] **Step 6: 运行测试**

Run: `uv run pytest -q tests/test_analytics_eval.py`
Expected: 全绿；报告包含 outcome + process 指标。

### Task 5.5: 多 Agent 编排 + 路由 + A/B 评测

**Files:**
- Create: `agentlab/analytics/multi_agent.py`
- Create: `agentlab/analytics/routing.py`
- Modify: `agentlab/analytics/graph.py`（暴露单 Agent 入口）
- Modify: `eval/run_analytics_eval.py`（增加 `--arch single|multi|auto`）
- Test: `tests/test_analytics_multi_agent.py`、`tests/test_analytics_routing.py`

**Interfaces:**
- `build_multi_agent_analytics_graph(model, db, checkpointer=None)`。
- `route_question(question: str, intent: dict) -> Literal["single", "multi"]`。
- `MultiAgentState`：`question`、`tenant_id`、`schema_brief`、`sql`、`result`、`critique`、`answer`、`steps`、`budget`。
- 角色：Supervisor、Scout、SQL Analyst、Critic、Reporter；`MAX_STEPS=6`。

- [ ] **Step 1: 写失败的拓扑测试**

用 fake model/db 测试：Supervisor 路由到 Scout → SQL Analyst → Critic → Reporter；Critic 失败回到 SQL Analyst；超过 `MAX_STEPS` 终止；Reporter 不重复执行 SQL。

- [ ] **Step 2: 写失败的路由测试**

简单单指标问题 → `single`；多指标/口径冲突/多跳/结果异常 → `multi`；歧义问题 → `clarify`（不进入 multi）。

- [ ] **Step 3: 实现 `multi_agent.py` 与 `routing.py`**

复用现有 `agentlab/agent/multi_agent.py` 的 `Command(goto=...)` 模式；共享状态；Critic 用结构化输出返回 `{faithful, feedback}`；失败默认不通过（与旧 multi-agent 的“失败默认通过”相反，避免静默错误）。

明确 **handoff 协议**：每个角色只消费/产出约定的 state 字段；Scout 产出 `schema_brief`，SQL Analyst 产出 `sql/result`，Critic 产出 `critique`，Reporter 只读结果不重复执行 SQL；禁止隐式上下文传递；检测重复步骤/重复查询。

- [ ] **Step 4: 写失败的 handoff/协作测试**

测试：Scout → SQL Analyst 的 `schema_brief` 非空；SQL Analyst → Critic 的 `sql/result` 完整；Critic 不通过时不进入 Reporter；Reporter 不重复执行 SQL；重复步骤被检测；`route_accuracy` 可统计。

- [ ] **Step 5: 运行测试**

Run: `uv run pytest -q tests/test_analytics_multi_agent.py tests/test_analytics_routing.py`
Expected: PASS。

- [ ] **Step 6: 50 条 golden 上做 single vs multi vs auto A/B**

Run: `uv run python -m eval.run_analytics_eval --limit 50 --arch single`  
Run: `uv run python -m eval.run_analytics_eval --limit 50 --arch multi`  
Run: `uv run python -m eval.run_analytics_eval --limit 50 --arch auto`

记录：task_success、P95、单任务成本、平均步骤数、SQL 修复次数、Critic 拦截率、route_accuracy、重复查询次数。  
**决策规则**：如果 multi 在复杂子集上没有显著提升（<5 个百分点）却显著增加成本/延迟，就默认 single，只对复杂题路由 multi，并把结论写进 README。

- [ ] **Step 7: 更新文档**

把 A/B 结果写进 `README` 和面试笔记；明确“多 Agent 不是默认，是数据证明后的路由选择”。

### Task 6: 成本、Prompt/Model 版本、Canary

**Files:**
- Create: `configs/analytics/prompts/*.yaml`、`agentlab/analytics/versioning.py`
- Test: `tests/test_analytics_versioning.py`

- [ ] **Step 1: 写失败的版本/成本测试**

prompt 版本被记录到 trace/audit；模型路由/成本上限生效；旧版本可回滚。

- [ ] **Step 2: 实现最小版本 registry 与 cost guard**

YAML 存 prompt 版本 + model id；运行时读取；审计记录版本；超预算返回可读错误。

- [ ] **Step 3: 运行测试**

Run: `uv run pytest -q`
Expected: 全绿。

---

# Week 4：API/CLI/图表、压测、SLO、交付

### Task 7: API + CLI + 图表

**Files:**
- Modify: `agentlab/api/app.py`、`services.py`、`schemas.py`
- Create: `agentlab/analytics/cli.py`
- Modify: `agentlab/api/static/index.html`
- Test: `tests/test_analytics_api.py`

**Files:**
- Modify: `agentlab/api/app.py`、`services.py`、`schemas.py`
- Create: `agentlab/analytics/cli.py`
- Create: `agentlab/analytics/session.py`
- Modify: `agentlab/api/static/index.html`
- Test: `tests/test_analytics_api.py`、`tests/test_analytics_session.py`

- [ ] **Step 1: 写失败的 API 测试**

`POST /analytics/chat`：返回 answer/sql/rows/chart_spec/audit_id；越权返回 403；歧义返回 clarification；SSE 流式事件包含 `plan_created`、`step_started`、`step_result`、`verification`、`replan`、`final`；`POST /analytics/cancel` 能取消任务。

- [ ] **Step 2: 写失败的多轮会话测试**

同一 session 追问“按地区拆一下”“换成上季度”“下钻到品类”能复用上一轮指标/过滤器；上下文超预算时压缩；不同 session 隔离。

- [ ] **Step 3: 实现路由、CLI、会话与流式计划**

`agentlab-analytics` console script；复用现有 JWT/thread 隔离；图表输出 Vega-Lite spec；页面展示表格 + 简单图 + 计划步骤进度；取消接口。

- [ ] **Step 4: 运行测试**

Run: `uv run pytest -q`
Expected: 全绿。

### Task 8: 压测 + 混沌 + SLO + Runbook

**Files:**
- Create: `scripts/load_analytics.py` 或 `scripts/load_analytics.js`
- Create: `docs/runbook-analytics.md`
- Create: `docs/interview-notes-analytics.md`
- Test: `tests/test_analytics_failure.py`

- [ ] **Step 1: 20/50 并发压测**

记录 P50/P95/P99、错误率、单任务成本；20 并发错误率 ≤1%。

- [ ] **Step 2: 混沌测试**

模型超时、DB 断连、SQL 错误、审批超时、SSE 断连、并行步骤部分失败、取消传播、预算超限；验证降级和审计。

- [ ] **Step 3: SLO/Runbook**

写清 SLI/SLO、告警、回滚、审批超时、DB 故障、权限告警。

- [ ] **Step 4: 最终演示与文档**

3 个场景：正常问答、歧义澄清、越权/高成本拒绝；更新 README、面试笔记、demo 脚本。

- [ ] **Step 5: 最终验收**

Run: `uv run pytest -q`（268 + 新测试全绿）  
Run: `RUN_INTEGRATION=1 uv run pytest -q -m integration`  
Run: 50 条评测 → 记录指标  
检查：越权 0、审计 100%、PII 0、P95/成本达标。

---

## 最终验收清单

- [ ] `uv run pytest -q` 全绿。
- [ ] `RUN_INTEGRATION=1 uv run pytest -q -m integration` 全绿。
- [ ] 50 条 golden：task_success ≥85%，permission_violation=0。
- [ ] 20 并发错误率 ≤1%；P95 ≤12s；单任务成本 ≤¥0.02。
- [ ] 每次查询有 audit row；日志/trace 无 PII。
- [ ] 歧义题澄清率、不可回答题拒答率有数据。
- [ ] 计划/编排指标：plan_validity、step_count、tool_selection_accuracy、replan_success、route_accuracy、critic_catch_rate 有数据。
- [ ] 并行执行、预算/取消、计划审批有测试和演示。
- [ ] 多 Agent A/B：single vs multi vs auto 的 task_success、P95、成本、步骤数有报告，默认架构有数据依据。
- [ ] README、runbook、面试笔记、demo 脚本齐全。
- [ ] 不构建应用 Docker 镜像；源码 `uv run`。
