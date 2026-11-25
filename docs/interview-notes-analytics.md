# 数据分析 Agent 面试口述稿

## 60 秒介绍

我做了一个面向多租户数仓的 Text-to-SQL 数据分析 Agent。它不是“让模型写 SQL”的 demo：有 sqlglot 只读守卫、只读数据库角色、PostgreSQL RLS 三层安全；有 50 条 golden 评测、真实 token 成本、CI 门禁；有成本守卫、审计、PII 脱敏、多轮会话和 SSE 计划进度。最后用 single / multi / auto 三套架构做了 50 条 A/B，用数据决定默认架构。

## 1. 为什么不用纯 ReAct

- 数据分析需要可解释的执行边界：理解 → 澄清/拒答 → 生成 SQL → 守卫 → 成本 → 执行 → 修复 → 回答。
- 显式状态机让每一步都能单独测试、单独观测、单独审计；ReAct 的自由循环很难回答“为什么这条 SQL 被执行”。
- repair 有上限（`MAX_REPAIRS=2`），避免模型在错误 SQL 上无限循环。

## 2. 三层 SQL 安全

- `sqlglot`：只允许单条 SELECT、表 allowlist、拒绝 DML/DDL/COPY/SET/系统 schema、默认/最大 LIMIT。
- 只读角色 `analytics_reader`：`default_transaction_read_only=on`，撤销写权限。
- RLS：每次查询 `SET LOCAL app.tenant_id`，9 张表启用 `tenant_isolation`；`order_items` 通过 `orders` EXISTS 隔离。
- PII：`customers_safe` 视图 `security_invoker=true`；原始 `customers` 只给安全列 SELECT；DB 错误/审计/日志统一 `redact_pii`。
- 越权测试：tenant_a 读 tenant_b/c 返回 0 行；跨租户问题在 understand 阶段直接 refuse。

## 3. 成本守卫

- `EXPLAIN (FORMAT JSON)` 解析 Total Cost，超过阈值触发 `interrupt` 人工审批。
- 没有 checkpointer/thread_id 时 fail closed，返回“需要人工审批”，不静默返回空状态。
- 坑：同一条净收入查询，CTE 形式成本 3.5k，标量子查询形式 152k；EXPLAIN 估算会误导，优先改写 SQL，不要盲目调阈值。
- 另有请求级模型调用预算（`ANALYTICS_REQUEST_BUDGET` / `ANALYTICS_MODEL_CALL_COST`），超预算返回可读答案，审计 `status=budget`。

## 4. 评测

- 50 条 golden：40 answer / 5 clarify / 5 refuse；覆盖 join、聚合、窗口、时间、退款、权限、PII、昂贵查询。
- 结果归一化：行顺序无关、`rel_tol=1e-9 + abs_tol=0.01`、空值/重复行严格计数；避免“格式差异”造成假阳性。
- 指标：task_success、execution_accuracy、clarification/refusal rate、P50/P95、真实 token/成本、route_accuracy、plan_validity、step_count、Critic 拦截率、9 类 failure class 与恢复率。
- CI：20 条 smoke + 越权 0 + PII 0 + task_success 回退 >3% 失败。
- 最终 50 条：task_success 1.0、越权 0、PII 0、P95 8.7s、平均成本 ¥0.0056（eval 真实 token）。
- 压测：20/50 并发错误率 0%，P95 8.2s，平均成本 ¥0.0062。

## 5. single vs multi vs auto

- multi：Supervisor → Scout → SQL Analyst → Critic → Reporter，`Command(goto=...)`，`MAX_STEPS=6`；Critic fail-closed，Reporter 不执行 SQL。
- A/B：single 1.000、multi 0.980、auto 1.000；复杂子集都是 17/17。
- multi 没有提升，但 P95 8.37s → 14.23s（+70%）、平均步骤 0.8 → 3.5、成本 +14.5%。所以默认 single，multi 只作为可选深分析模式。
- forced multi 的 0.98 来自 Scout 把一条歧义题判成 answer；auto 在进入 multi 前已把 clarify/refuse 留在 single，所以 auto 仍是 1.000。
- 结论：多 Agent 不是默认，是数据证明后的路由选择；要成为默认，必须在复杂子集上看到 ≥5 个百分点的提升。

## 6. 真实调试故事

1. **MRR 多算了 status 过滤**：模型在日期口径外又加了 `status='active'`，与 catalog 定义不一致；修复是口径写死“仅按日期，不额外过滤 status”。
2. **跨租户被回答成 tenant_a**：请求 tenant_b 时模型过滤 tenant_a 并解释“查的是 tenant_a”；修复是 understand prompt 直接 refuse 跨租户/PII 请求，SQL prompt 强制 tenant_id 等于给定租户。
3. **AnswerOutput 解析 null**：整个请求变 error；修复是保留已查到的 result，用确定性文字兜底，不让“解释失败”丢掉正确答案。
4. **HITL 无 checkpointer 静默空状态**：修复为 fail closed，返回“需要人工审批”。
5. **CI clarify 抖动**：“上个月退款情况如何”偶尔被 answer；prompt 明确“相对时间不算明确时间范围”，5 条 clarify 复测通过。
6. **结果归一化误判**：固定 `round(2)` 无法处理大数相对误差和 0.01 绝对容差；改为 `math.isclose` + 逐行顺序无关匹配。

## 7. 取舍与限制

- 合成数仓、固定 seed；golden 绑定 scale=1.0，换数仓要重算 expected_result。
- 多步计划库已实现（planning/verification/executor），默认图仍是单 SQL；`unnecessary_steps` 只统计重复 SQL。
- 会话表是进程内实现；生产要换 Redis/Postgres。
- retry/circuit breaker 已实现但默认未接线；高并发下依赖模型供应商配额。
- 图表是模型返回 Vega-Lite spec，页面只做简单条形图兜底。
- 没有真实语义层/dbt，指标口径写在 `catalog.py`。

## 8. 如果面试官追问

- **为什么 PostgreSQL**：现有栈 + RLS + EXPLAIN + pgvector；MySQL-only 在 AI/Agent 样本里很少。
- **怎么证明安全**：三层防御 + 越权/PII 测试 + 审计 request_id + CI 门禁。
- **怎么控制成本**：EXPLAIN 成本守卫 + 请求预算 + 真实 token 统计 + eval 成本上限。
- **为什么多 Agent 没默认**：A/B 没有复杂子集提升，延迟/步骤/成本都更高。
- **下一步**：语义层/数仓适配器、BIRD/Spider 子集、真实用户 SLO、多步计划接线。
