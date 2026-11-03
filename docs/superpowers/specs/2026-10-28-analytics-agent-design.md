# 企业数据分析 Agent（Analytics Agent）设计

**日期：** 2026-10-28  
**状态：** 待评审  
**起点：** 现有 `langchain-demo` / `agentlab` 包（268 个离线测试、LangGraph、HITL、RAG、eval、Postgres）

## 1. 目标

做一个**生产级参考切片**：用户用自然语言问业务数据问题，Agent 完成

> 理解问题 → 识别歧义 → 选择指标/表 → 生成 SQL → 安全校验 → 执行 → 失败修复 → 解释结果/图表 → 审计

重点不是“能查数”，而是**安全、可评测、可观测、可恢复**。

### 成功标准

- 50 条 golden 任务：task_success ≥ 85%
- 越权/写操作/危险 SQL：0 次成功
- 审计覆盖率：100%
- P95 端到端 ≤ 12s（本地 CPU，按 baseline 校准）
- 单任务成本 ≤ ¥0.02
- 20 并发错误率 ≤ 1%
- SQL 错误自动修复成功率可度量
- 歧义问题澄清率、不可回答问题拒答率可度量

## 2. 非目标

- 不做多租户平台、SSO、计费、运营后台
- 不做 K8s/Terraform；本地 Docker 只跑 Postgres/Redis 等依赖
- 不做微调/vLLM/SGLang
- 不做完整 BI 前端；图表先输出 Vega-Lite spec + 简单 HTML 表格
- 不构建应用 Docker 镜像；源码用 `uv run`

## 3. 用户场景

1. **运营**：上个月华东区退款率最高的三个品类是什么？
2. **财务**：本季度 MRR 环比变化，按套餐拆分。
3. **销售**：过去 30 天新增客户数、转化率、ARPU。
4. **客服**：工单量按类别和优先级分布，平均解决时长。
5. **歧义**：“最近收入怎么样？”——需要澄清时间范围和收入口径。
6. **越权**：用户 A 试图查询用户 B/其他租户的数据。
7. **高成本**：全表扫描/大范围导出——需要审批或拒绝。
8. **不可回答**：数据里没有的指标——应明确说无法回答，而不是编造。

## 4. 总体架构

```text
CLI / FastAPI
   │
   ▼
Analytics Graph (LangGraph)
   ├─ understand：意图、指标、时间范围、歧义检测
   ├─ clarify：信息不足时中断，向用户提问
   ├─ plan_sql：基于 schema/metric catalog 生成 SQL
   ├─ validate_sql：sqlglot + allowlist + 只读 + LIMIT + 超时
   ├─ approve：高成本查询/导出 HITL（interrupt）
   ├─ execute：只读连接 + RLS + statement_timeout
   ├─ repair：错误 SQL 回喂模型，最多 2 次
   ├─ answer：解释结果、引用指标口径、生成图表 spec
   └─ audit：记录问题、SQL、行数、成本、耗时、审批
   │
   ▼
Postgres（analytics schema）
   ├─ 业务表 + 指标目录 + 审计表
   ├─ RLS（tenant_id）
   └─ 只读角色 analytics_reader
```

## 4.1 多 Agent 编排（受控变体）

单 Agent 是基线；多 Agent 是**需要被数据证明的变体**，不是默认架构。

```text
Supervisor（路由/预算/终止）
   ├─ Scout：选表、找指标口径、识别数据缺口
   ├─ SQL Analyst：写 SQL、调用 validate/execute/repair
   ├─ Critic：检查 SQL 是否回答问题、结果是否异常、引用/口径是否正确
   └─ Reporter：生成最终解释 + 图表 spec
```

- **共享状态**：question、tenant、schema_brief、sql、result、critique、answer、steps、budget。
- **路由**：简单问题走单 Agent；涉及多指标、口径冲突、多跳、结果异常时走多 Agent。
- **终止**：`MAX_STEPS`、token/成本预算、Critic 通过、无进展检测。
- **HITL**：Critic 不通过或高成本查询仍走人工审批。
- **评测**：50 条 golden 上做 single vs multi A/B，比较 task_success、P95、单任务成本、步骤数、修复次数。
- **原则**：如果多 Agent 在复杂题上没有显著收益、却显著增加延迟/成本，就默认单 Agent，并在文档里写清取舍；这本身就是高级信号。

## 4.2 Agent 架构与编排能力

单 Agent 的显式工作流只是起点；下面这些能力单独设计、单独测试、单独评测。

### 4.2.1 计划表示与任务分解

- `PlanStep`：`id`、`goal`、`kind`（query/verify/clarify/chart）、`depends_on`、`metric_ids`、`expected_output`、`status`、`result_ref`。
- `AnalyticsPlan`：`question`、`steps`、`assumptions`、`clarification_needed`、`max_steps`、`version`。
- Planner 先判断：单步查询还是多步分析（多指标、多跳、口径冲突、需要交叉验证）。
- 计划校验：DAG 无环、工具/指标在 allowlist、步骤预算、每步有验收条件。
- 计划审批：步骤数/预估成本超过阈值，或涉及导出/高风险操作时，`interrupt` 展示计划，允许用户批准/编辑。

### 4.2.2 执行、并行与合并

- 依赖就绪的步骤才执行；独立步骤用 LangGraph `Send` 并行 fan-out。
- 每个步骤独立校验/执行/结果，fan-in 时合并、去重、处理部分失败。
- 最大并发、单步超时、整体 deadline；部分失败不能让整个任务丢结果。
- 每个步骤作为独立 super-step 落 checkpoint，支持断点续跑。

### 4.2.3 验证、反思与重规划

- 每步验收：SQL 成功、行数/空值/异常值、结果形状是否符合 `expected_output`、指标口径是否一致。
- 最终验收：回答是否覆盖所有计划步骤、是否引用指标定义、是否有证据不支持的结论。
- 失败分类：歧义、schema 缺口、指标口径冲突、SQL 错误、空结果、权限、成本、模型/工具错误。
- 恢复策略：SQL 错误 → repair；空结果/太宽 → 缩小范围或换指标；schema/口径 → 澄清；权限 → 拒绝并说明；成本 → 审批或降级。
- 重规划：最多 2 次；检测无进展、目标漂移、重复步骤；超过预算终止。

### 4.2.4 工具 / Skill 注册与动态选择

- `SkillSpec`：名称、描述、输入/输出 Schema、权限、预估成本/延迟、允许角色/租户。
- 运行时按角色/租户/问题动态给出工具子集；`list_skills` 可发现。
- 评测 tool selection accuracy：期望工具 vs 实际工具；记录无用调用、重复调用。

### 4.2.5 预算、终止与取消

- `Budget`：最大步骤、token、成本、墙钟时间、并发数。
- 每个节点扣减；超预算返回可读原因。
- 无进展检测、循环检测、`MAX_STEPS`、`MAX_REPLANS`。
- 取消传播：API 取消/SSE 断连 → 取消子步骤；已执行步骤保留结果和审计。

### 4.2.6 多轮分析与会话状态

- `SessionState`：上一轮计划、指标、过滤器、结果引用、用户偏好。
- 支持追问/下钻/改时间范围/换维度，不用从零重问。
- 长会话做 context compaction；schema/metric catalog 按需检索，不整包塞 prompt。

### 4.2.7 可观测与轨迹评测

- 计划 trace：plan_created、step_started、step_result、verification、replan、final。
- 轨迹指标：plan validity、step count、tool selection accuracy、unnecessary steps、replan success、route accuracy（single vs multi）、critic catch rate、cost per step。
- 失败分类统计与恢复率；badcase 可一键回流 golden。

### 4.2.8 架构决策记录（ADR）

用 ADR 明确：
- 为什么基线是 **Plan-and-Execute + 局部 ReAct/repair**，而不是纯 ReAct 或纯多 Agent；
- 为什么多 Agent 是受控变体，按路由启用；
- 什么情况下改用多 Agent/并行/单 Agent；
- 每种选择的延迟、成本、失败模式。

### 4.2.9 不做（本轮）

- 不做通用 A2A 协议、Agent 市场、跨组织 agent 发现；
- 不做通用代码沙箱/浏览器；
- 不做无限自主的长时任务；只做到受控长任务 + 断点续跑。

## 5. 数据模型与合成数据

### 业务表（示例 SaaS）

| 表 | 关键字段 | 说明 |
|---|---|---|
| `customers` | customer_id, tenant_id, region, segment, created_at | 客户 |
| `products` | product_id, tenant_id, category, unit_price, active | 产品 |
| `orders` | order_id, tenant_id, customer_id, order_date, status, channel, region | 订单 |
| `order_items` | order_id, product_id, quantity, unit_price, discount | 订单明细 |
| `refunds` | refund_id, tenant_id, order_id, refund_date, amount, reason | 退款 |
| `subscriptions` | subscription_id, tenant_id, customer_id, plan, mrr, start_date, end_date, status | 订阅 |
| `usage_events` | event_id, tenant_id, customer_id, event_date, feature, count | 使用事件 |
| `tickets` | ticket_id, tenant_id, customer_id, created_at, category, status, priority | 工单 |
| `metric_catalog` | metric_id, tenant_id, name, definition, sql_expression, version | 指标口径 |
| `analytics_audit` | request_id, user_id, tenant_id, question, sql, status, row_count, estimated_cost, duration_ms, approved_by, created_at | 审计 |

### 合成数据原则

- **确定性 seed**：同一份数据可复现。
- **规模**：10k customers、500 products、100k orders、300k order_items、8k refunds、5k subscriptions、500k usage_events、20k tickets。
- **脏数据**：空值、重复、取消/退款订单、测试账号、时区、折扣、部分月缺失。
- **多租户**：至少 3 个 tenant，数据分布不同，用于越权测试。
- **指标口径冲突**：`revenue` vs `gmv` vs `net_revenue` 在 `metric_catalog` 里定义清楚。
- **PII**：姓名/邮箱/电话全假；`customers_safe` 视图脱敏。

### 生成方式

- `agentlab/analytics/seed.py`：Python + Faker + 固定 seed，批量 INSERT。
- `scripts/start_analytics_db.sh`：复用现有 pgvector 容器，创建 `analytics` schema、只读角色、RLS policy、视图。
- 数据生成脚本幂等：`--reset` 可重建。

## 6. Agent 流程与工具

### 图节点

| 节点 | 职责 | 输出 |
|---|---|---|
| `understand` | 解析问题、识别指标/维度/时间范围/歧义 | `intent` |
| `clarify` | 信息不足时 `interrupt`，向用户提问 | 用户回答 |
| `plan_sql` | 基于 schema + metric catalog 生成 SQL | `sql` |
| `validate_sql` | 只读、单语句、allowlist、LIMIT、超时 | 通过/拒绝 |
| `approve` | 预估成本超阈值/导出时 HITL | 审批结果 |
| `execute` | 只读连接 + RLS + `statement_timeout` | 结果行/错误 |
| `repair` | 错误回喂模型，最多 2 次 | 新 SQL |
| `answer` | 解释、引用口径、图表 spec | 自然语言 + chart |
| `audit` | 写审计表 | 完成 |

### 工具

- `list_tables()`：列出允许访问的表/视图。
- `describe_table(name)`：字段、类型、含义、示例值。
- `get_metric_definition(name)`：返回口径、SQL 表达式、版本。
- `run_sql(sql)`：内部节点使用；对外不直接暴露原始 SQL 执行。
- `make_chart(rows, chart_type)`：返回 Vega-Lite spec。
- `export_report(...)`：HITL 审批后导出。

## 7. 安全与权限

1. **只读角色**：`analytics_reader` 只对 `analytics` schema 有 SELECT；应用不使用 postgres 超级用户。
2. **RLS**：所有业务表带 `tenant_id`；查询前 `SET LOCAL app.tenant_id = %s`；policy 强制过滤。
3. **SQL 守卫**：
   - `sqlglot` 解析，只允许单条 `SELECT`。
   - 拒绝 DDL/DML/多语句/`COPY`/`SET`/`pg_catalog`/`information_schema`。
   - 表/视图 allowlist；禁止系统表。
   - 强制 `LIMIT`（默认 200，最大 1000）。
   - `statement_timeout=5s`。
4. **成本守卫**：`EXPLAIN (FORMAT JSON)` 估算 cost；超过阈值走 HITL 或拒绝。
5. **PII**：Agent 只能查 `customers_safe` 等脱敏视图；结果再做一次正则脱敏兜底。
6. **审计**：每次查询记录 user、tenant、question、SQL、状态、行数、估算成本、耗时、审批人。
7. **注入**：用户问题、检索内容、工具结果都视为不可信；SQL 只能由模型生成后经守卫校验，不能直接拼接用户输入。

## 8. 评测

- `eval/analytics_golden.jsonl`：50 条
  - 40 条可回答
  - 5 条歧义（期望澄清）
  - 5 条不可回答（期望拒答）
- 每条字段：question、tenant、expected_sql、expected_result、expected_outcome、difficulty、tags。
- 指标：
  - **execution_accuracy**：Agent SQL 结果与 expected_result 一致（顺序不敏感、数值容差）
  - **answer_correctness**：LLM judge（1–5）
  - **clarification_rate**：歧义题是否澄清
  - **refusal_rate**：不可回答题是否拒答
  - **permission_violation**：越权查询成功次数（必须 0）
  - **cost/latency**：单任务 token/成本/P50/P95
  - **repair_success**：首次 SQL 失败后修复成功比例
  - **plan_validity**：计划是否合法（DAG、工具/指标 allowlist、预算）
  - **step_count / unnecessary_steps**：步骤数与无效步骤
  - **tool_selection_accuracy**：期望工具 vs 实际工具
  - **replan_success**：重规划后通过验收的比例
  - **route_accuracy**：single vs multi 路由是否符合预期
  - **critic_catch_rate**：Critic 拦截错误 SQL/结果的比例
- 失败分类：歧义、schema 缺口、指标口径冲突、SQL 错误、空结果、权限、成本、模型/工具错误；统计每类恢复率。
- 反例集：多语句、DDL、`pg_catalog`、跨租户、昂贵查询、PII 查询、计划越界、重复步骤。

## 9. 可观测与可靠性

- **Trace**：`analytics.understand`、`analytics.plan`、`analytics.plan.validate`、`analytics.step.execute`、`analytics.verify`、`analytics.replan`、`analytics.answer`。
- **Metrics**：查询数、错误率、P50/P95、行数、估算成本、token 成本、权限拒绝数、澄清率、修复成功率、计划步骤数、并行度、重规划次数、预算超限次数。
- **日志**：结构化 JSON，带 request_id、user_id、tenant_id（不记录原始 PII）。
- **可靠性**：
  - DB 连接重试/超时；SQL 错误最多修复 2 次。
  - 模型超时/失败降级为“无法回答 + 原因”。
  - 高成本查询需要审批；审批超时自动取消。
  - SSE 断连清理。
- **SLO**：task_success ≥85%、P95 ≤12s、错误率 ≤1%、单任务成本 ≤¥0.02。

## 10. 与现有项目集成

新增子包 `agentlab/analytics/`：

```text
agentlab/analytics/
  __init__.py
  config.py          # ANALYTICS_* 环境变量
  catalog.py         # schema/metric catalog
  sql_guard.py       # sqlglot 校验
  db.py              # 只读连接、RLS、EXPLAIN、执行
  tools.py           # list/describe/metric/run_sql/chart/export
  graph.py           # build_analytics_graph（单 Agent 基线）
  planning.py        # PlanStep/AnalyticsPlan、planner、计划校验
  executor.py        # 步骤执行、并行 fan-out/fan-in、合并
  verification.py    # 步骤/最终验收、失败分类
  registry.py        # SkillSpec、动态工具子集
  budget.py          # step/token/cost/time 预算、取消传播
  session.py         # 多轮分析状态、追问/下钻
  multi_agent.py     # Supervisor + Scout/SQL Analyst/Critic/Reporter
  routing.py         # simple vs multi 路由
  seed.py            # 合成数据
  eval.py            # 评测辅助
```

- `agentlab/config.py` 增加 `ANALYTICS_DATABASE_URL`、`ANALYTICS_MAX_ROWS`、`ANALYTICS_STATEMENT_TIMEOUT`、`ANALYTICS_COST_THRESHOLD`、`ANALYTICS_TENANT_ID`。
- `pyproject.toml` 增加 `sqlglot`、`faker` 依赖。
- `agentlab/api/services.py` 增加 `analytics_graph`；`app.py` 增加 `/analytics/chat`、`/analytics/chat/stream`。
- `agentlab/analytics/multi_agent.py` 提供多 Agent 变体；路由由 `routing.py` 决定，默认单 Agent。
- `docs/adr/2026-10-28-analytics-agent-architecture.md` 记录架构决策（Plan-and-Execute vs ReAct vs 多 Agent）。
- 新 console script：`agentlab-analytics`（CLI 演示）。
- `scripts/start_analytics_db.sh`：建 schema、表、视图、角色、RLS、种子数据。
- `eval/analytics_golden.jsonl` + `eval/run_analytics_eval.py`。
- 现有 RAG Agent 行为不变；新增测试独立。

## 11. 风险与取舍

| 风险 | 应对 |
|---|---|
| SQL 守卫被绕过 | sqlglot AST + 只读角色 + RLS 三层防御 |
| RLS 配置错误导致越权 | 集成测试 + 反例集 + 审计告警 |
| 合成数据太干净 | 故意加入空值、重复、退款、时区、口径冲突 |
| 歧义题被硬答 | `clarify` 节点 + 歧义 golden + 指标 |
| 高成本查询拖垮 DB | EXPLAIN cost 阈值 + statement_timeout + HITL |
| LLM 生成错误 SQL | 错误回喂修复 + execution accuracy 评测 |
| 评测结果被 LLM judge 偏差影响 | execution accuracy 为主，judge 为辅 |
| 多 Agent 增加延迟/成本却无收益 | A/B 评测 + 默认单 Agent + 复杂题路由 |
| 过度规划/计划漂移 | `MAX_STEPS`/`MAX_REPLANS`、每步 `expected_output`、无进展检测 |
| 并行步骤部分失败/重复执行 | 每步幂等键、fan-in 合并、部分失败降级 |
| 预算失控 | `Budget`（步骤/token/成本/时间/并发）、超限终止 |
| 动态工具选择错误 | `SkillSpec` + tool selection accuracy + allowlist |
| 4 周做不完 | 砍平台化/UI/多副本；保留计划/验证/评测/安全 |

## 12. 4 周里程碑

- **Week 1**：合成数据 + 只读连接 + SQL 守卫 + 基础图 + 20 条 golden + ADR。
- **Week 2**：RLS/审计/PII/歧义/修复 + 计划/并行/验证/预算 + 可靠性 + 可观测。
- **Week 3**：50 条 golden + eval runner + 过程指标/失败分类 + CI 门禁 + 多 Agent A/B + 成本/版本。
- **Week 4**：API/CLI/图表 + 多轮会话/流式计划 + 压测/混沌 + SLO/runbook + 面试材料。

详细任务见 `docs/superpowers/plans/2026-10-28-analytics-agent-4-week.md`。
