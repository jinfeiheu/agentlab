# ADR-0001：数据分析 Agent 的编排架构

- **日期**：2026-10-28（决策），2026-11-04（实施记录）
- **状态**：Accepted
- **关联**：
  - `docs/superpowers/specs/2026-10-28-analytics-agent-design.md`
  - `docs/superpowers/plans/2026-10-28-analytics-agent-4-week.md`
  - `agentlab/analytics/graph.py`
- **决策**：以**单 Agent + 显式 Plan-and-Execute + 局部 repair** 为默认架构；多 Agent 是受控变体，只有 A/B 数据证明有收益时才按路由启用。

## 1. 背景

数据分析 Agent 要做的事是：

> 自然语言问题 → 意图/歧义识别 → 生成 SQL → 安全校验 → 执行 → 失败修复 → 解释/图表 → 审计

它不是“能查数”的 demo，而是**安全、可评测、可观测、可恢复**的生产级切片。约束是：

- 4 周交付，单人开发；
- 复用现有 `agentlab` 仓库（LangGraph、FastAPI、Postgres、eval）；
- 没有真实生产流量，只有确定性合成数据；
- 安全目标：越权 0、PII 0、审计 100%；
- 性能目标：P95 ≤ 12s、单任务成本 ≤ ¥0.02。

因此架构选择的第一优先级不是“最智能”，而是**可控、可验证、可解释**。

## 2. 决策驱动因素

1. **SQL 安全不可绕过**：模型生成的 SQL 必须先经过 `sqlglot` 守卫、只读角色和 RLS，不能直接执行。
2. **评测需要稳定轨迹**：execution accuracy、repair 次数、澄清率都需要明确的节点和状态字段。
3. **审计需要每一步可追踪**：问题、SQL、校验结果、执行结果、审批人都要能落到 `analytics_audit`。
4. **成本/延迟可控**：多一次模型调用就是一次成本和延迟；不能为了“看起来高级”上多 Agent。
5. **4 周可交付**：先做单 Agent 基线，再用数据决定是否加多 Agent/并行。
6. **可演进**：Week 2 加计划/验证/并行，Week 3 加多 Agent A/B，不推翻基线。

## 3. 考虑的方案

### 方案 A：纯 ReAct

模型在循环里自主决定调用哪个工具：`list_tables`、`describe_table`、`run_sql`、`make_chart`，直到给出答案。

**优点**
- 实现最短，灵活，适合探索型问题；
- 工具组合不受预定义流程限制。

**缺点**
- 模型可以直接调用 `run_sql`，安全门禁必须在工具层再包一层，容易漏；
- 步数、成本、延迟不可预测，评测和审计困难；
- SQL 错误后的行为不稳定，可能反复重试或跳过校验；
- 对“歧义/不可回答”缺少强制分支，容易硬答。

**结论**：不作为主架构。可以在 `repair`、`clarify` 这类局部决策里保留 ReAct 的灵活性，但外层编排必须显式。

### 方案 B：Plan-and-Execute + repair（选中）

显式节点：

```text
understand → clarify / refuse
          → plan_sql → validate_sql → execute → repair（最多 2 次）→ answer
```

**优点**
- `validate_sql` 是 SQL 进入数据库前的唯一入口，安全边界清晰；
- 每个节点都有明确输入/输出，评测和审计可以直接读 state；
- repair 次数有上限，成本和延迟可控；
- 歧义/不可回答是显式分支，不会“硬答”；
- 后续可以在 `plan_sql` 前插入 planner，在 `execute` 后插入 verifier，不推翻主流程。

**缺点**
- 灵活性低于 ReAct，复杂多跳问题需要多步计划；
- 需要维护状态机和路由条件；
- 计划和 SQL 的质量仍然依赖模型。

**结论**：Week 1 默认架构。

### 方案 C：Reflexion / Critic

在生成 SQL 或答案后，增加一个 Critic 检查：SQL 是否回答问题、结果是否异常、口径是否正确；不通过则回退重写。

**优点**
- 能拦截“SQL 能跑但答错”的错误；
- 对口径冲突、结果异常值有帮助；
- 可以用结构化输出量化 `critic_catch_rate`。

**缺点**
- 每次检查增加 1–2 次模型调用，P95 和成本上升；
- Critic 自身会误判（false pass / false fail），需要评测；
- 如果 Critic 和生成器用同一个模型，容易共享盲点。

**结论**：不作为 Week 1 默认，作为 Week 2 的 `verification` 层和 Week 3 多 Agent 中的 Critic 角色；是否默认启用由 A/B 决定。

### 方案 D：Supervisor 多 Agent

角色：Supervisor、Scout、SQL Analyst、Critic、Reporter。

```text
Supervisor → Scout（选表/口径）→ SQL Analyst（生成/执行/修复）
           → Critic（检查）→ Reporter（解释/图表）
```

**优点**
- 角色职责清晰，适合多指标、多跳、口径冲突的复杂问题；
- 可以并行 Scout 多个数据源；
- 每个角色只消费/产出约定字段，便于测试 handoff。

**缺点**
- 调用次数和 token 成本显著增加；
- handoff 丢字段、Reporter 重复执行 SQL、Critic 误判都是真实失败模式；
- Supervisor 路由错误会把简单问题送进复杂流程；
- 没有 50 条 golden 的 A/B 数据，不能证明收益。

**结论**：Week 3 作为受控变体实现，默认不启用；只对复杂问题路由，并用 `route_accuracy`、`critic_catch_rate`、重复查询次数验证。

### 方案 E：并行 fan-out/fan-in

对无依赖的步骤（例如两个独立指标查询）用 LangGraph `Send` 并行执行，再 fan-in 合并。

**优点**
- 独立步骤的墙钟时间下降；
- 适合“多指标对比”“多数据源交叉验证”。

**缺点**
- 部分失败、取消传播、结果合并、重复执行都需要额外设计；
- 峰值并发和 token 成本上升；
- 并行度受 DB 连接数和 `max_concurrency` 限制。

**结论**：Week 2 Task 4.6 实现，作为执行器能力；默认串行，只有独立步骤才并行。

## 4. 方案对比

> 下表除“当前 baseline”外均为**设计估计**，不是实测值；Week 3 A/B 会用 50 条 golden 校准。

| 方案 | 典型模型调用数 | P95 延迟 | 成本 | 安全可控 | 可评测 | 主要失败模式 | 采用阶段 |
|---|---|---|---|---|---|---|---|
| 纯 ReAct | 3–8，方差大 | 高 | 中高 | 低–中 | 中 | 循环、越权、难审计 | 不采用 |
| Plan-and-Execute + repair | 2–5 | **低–中** | **低** | **高** | **高** | 计划无效、修复循环 | **Week 1 默认** |
| Reflexion / Critic | +1–2 | +30–80% | +30–100% | 高 | 高 | Critic 误判 | Week 2 验证层 |
| Supervisor 多 Agent | 5–10 | +50–150% | +2–4x | 高（有协议时） | 中高 | handoff 丢字段、重复查询 | Week 3 受控变体 |
| 并行 fan-out/fan-in | 与串行相同 | 独立步骤下降 | 峰值上升 | 高 | 中高 | 部分失败、取消传播 | Week 2 执行器 |

当前实测 baseline（20 条 golden，2026-11-04）：

- task_success **1.0**、execution_accuracy **1.0**、clarification_rate **1.0**、refusal_rate **1.0**
- permission_violation **0**
- P50 **4.70s**、P95 **7.51s**
- 平均单任务成本估算 **¥0.00045**
- 报告：`eval/results/analytics-baseline.json`

说明：首轮 baseline 是 0.75 / 0.6429，原因是 `aov`、`net_revenue`、`order_count`、`mrr` 的口径没写清；修正指标目录后达到 1.0。20 条样本较小，Week 3 扩到 50 条并加入 join、窗口、权限、昂贵查询后，这个数字会下降，才是真实门槛。

## 5. 决策

### Week 1：单 Agent 显式工作流

```text
START → understand → (clarify | refuse | plan_sql)
plan_sql → validate_sql → (execute | repair)
execute → (answer | repair)
repair → validate_sql（最多 2 次）
answer → END
```

- `understand` 输出 `Intent`：answer/clarify/refuse + metrics/dimensions/time_range；
- `plan_sql` 输出单条 SELECT；
- `validate_sql` 调用 `sqlglot` 守卫 + allowlist；
- `execute` 调用只读 `AnalyticsDB`；
- `repair` 把错误回喂模型，最多 2 次；
- `answer` 输出中文解释 + Vega-Lite `chart_spec`。

### Week 2：在基线上加能力，不换主架构

- `Task 3`：RLS、审计、PII、歧义测试；
- `Task 4`：可靠性、可观测、成本守卫、HITL 审批；
- `Task 4.5`：`PlanStep`/`AnalyticsPlan`、计划校验、验证/反思、最多 2 次重规划；
- `Task 4.6`：并行执行、Skill 注册、预算/取消。

### Week 3：多 Agent 作为受控变体

- 实现 Supervisor + Scout/SQL Analyst/Critic/Reporter；
- 加 `route_question`：简单问题走 single，复杂问题走 multi；
- 50 条 golden 上做 single vs multi vs auto A/B；
- **默认仍为 single**，除非复杂子集提升 ≥5 个百分点且成本/延迟可接受。

### Week 4：暴露接口

- API `/analytics/chat`、CLI、图表、多轮会话；
- 压测/混沌/SLO/runbook；
- 面试材料与 demo。

## 6. 为什么不是纯 ReAct

1. **安全边界**：纯 ReAct 让模型决定是否调用 `run_sql`。即使工具层有守卫，模型仍可能绕过校验、拼接多条语句或调用未授权表。显式工作流把 `validate_sql` 放在唯一执行入口之前，模型无法跳过。
2. **可评测性**：execution accuracy、repair 次数、澄清率、权限拒绝都需要稳定字段。ReAct 的轨迹是模型自由生成的，评测要额外解析自然语言。
3. **成本上限**：ReAct 的循环次数不可预测；显式图可以用 `MAX_REPAIRS=2`、预算和超时强制终止。
4. **审计**：每一步的 SQL、校验原因、行数、耗时都能直接落表；ReAct 需要从消息历史反推。

局部 ReAct 仍然保留：`repair` 节点让模型根据错误自由重写 SQL，`understand` 节点让模型决定澄清/拒答。**外层确定性，内层灵活性**。

## 7. 为什么多 Agent 不是默认

1. **成本放大**：Supervisor + Scout + Analyst + Critic + Reporter 至少 5 次模型调用，复杂问题更多；单 Agent 通常 2–5 次。
2. **协调失败**：handoff 丢字段、Reporter 重复执行 SQL、Critic 与生成器共享盲点，都是多 Agent 特有的失败模式。
3. **没有证据**：20 条 baseline 上单 Agent 已经 1.0；多 Agent 在简单题上只会增加延迟和成本。
4. **高级信号**：能说“我做了 A/B，数据证明默认 single”比“我上了多 Agent”更有说服力。

**决策规则**：如果 multi 在复杂子集上没有 ≥5 个百分点提升，却显著增加成本/延迟，就默认 single，只对复杂题路由 multi，并把结论写进 README 和面试笔记。

**路由条件**（Week 3 实现）：
- 多个指标/多跳查询；
- 指标口径冲突；
- 结果异常（空结果、行数异常、数值异常）；
- 需要交叉验证的导出/高成本查询。

## 8. 后果

### 正面

- SQL 执行前有唯一安全门禁，RLS/只读角色/审计可以分层验证；
- 状态字段稳定，execution accuracy 和过程指标可直接计算；
- 模型、DB、checkpointer 都可注入，离线测试不需要真实 API/Postgres；
- 多 Agent/并行/验证都是增量能力，不推翻基线。

### 负面

- 灵活性低于纯 ReAct，复杂多跳问题需要显式 planner；
- 代码量大于 demo，节点/路由/状态需要维护；
- 多 Agent A/B 需要额外状态字段和 handoff 测试；
- `json_mode` 的结构化输出约束弱于 function calling，需要 Pydantic 校验和评测兜底。

### 风险与缓解

| 风险 | 缓解 |
|---|---|
| 指标口径漂移 | `catalog.py` 作为单一来源；seed 的 `metric_catalog` 与 prompt 共用；golden 与口径对齐 |
| 20 条 golden 过拟合 | Week 3 扩到 50 条，加入 join/窗口/权限/昂贵查询/badcase |
| 纯 ReAct 式越权 | 不向模型暴露原始执行工具；`validate_sql` 唯一入口；只读角色 + RLS |
| 多 Agent 成本失控 | 默认 single；`MAX_STEPS`/预算/路由；A/B 决策规则 |
| 并行部分失败 | 每步独立结果、fan-in 合并、取消传播、审计保留 |
| 本地规模不代表生产 | Week 4 压测/混沌；README 明确“参考切片，不是生产平台” |

## 9. 验收与后续

- Week 3 在 50 条 golden 上跑 `single` / `multi` / `auto`，记录：
  - task_success、P95、单任务成本、平均步骤数；
  - SQL 修复次数、Critic 拦截率、route_accuracy、重复查询次数。
- CI 门禁：task_success 回退 >3% 失败；permission_violation >0 失败；PII 泄露失败。
- 如果多 Agent 没有显著收益，README 和面试笔记明确写“默认 single，复杂题路由 multi”。

## 10. 参考

- 设计文档：`docs/superpowers/specs/2026-10-28-analytics-agent-design.md`
- 实施计划：`docs/superpowers/plans/2026-10-28-analytics-agent-4-week.md`
- 图实现：`agentlab/analytics/graph.py`
- 指标目录：`agentlab/analytics/catalog.py`
- 评测：`eval/run_analytics_eval.py`、`eval/analytics_golden.jsonl`
- Baseline：`eval/results/analytics-baseline.json`
