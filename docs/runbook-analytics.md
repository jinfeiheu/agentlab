# Analytics Agent Runbook

## 1. 服务边界

- 入口：`POST /analytics/chat`、`POST /analytics/chat/stream`、`POST /analytics/cancel`、`GET /analytics`；CLI `agentlab-analytics`。
- 依赖：DeepSeek API、Postgres（analytics 数仓 + audit 写库）、只读角色 `analytics_reader`。
- 安全边界：JWT → `UserContext.tenant_id`；SQL 守卫 + 只读角色 + RLS 三层；PII 在 DB 错误、审计、日志、SSE 中统一脱敏。
- 默认架构：单 Agent 显式状态机。multi 不是默认，见 README 的 A/B 结论。

## 2. SLI / SLO

| SLI | 目标（SLO） | 观测方式 |
|---|---|---|
| 请求成功率 | ≥ 99%（20 并发错误率 ≤ 1%） | API 5xx/超时；`analytics_query` 日志 |
| task_success | ≥ 85%（50 条 golden） | `eval.run_analytics_eval` |
| 延迟 P95 | ≤ 12s | eval / load test / OTel span |
| 单任务成本 | ≤ ¥0.02 | eval `TokenUsageTracker` |
| 越权 | 0 | `permission_violation`、`analytics_audit` |
| PII 泄露 | 0 | `pii_leaks`、日志/trace 抽查 |
| 审计覆盖 | 100% 公共入口 | `analytics_audit.request_id` |
| 步骤审计 | plan 模式每步一行 | `analytics_audit_steps` |
| Critic 拦截率 | 有数据 | multi A/B 报告 |

### 最近压测（Direct graph，DeepSeek，auto-approve）

| 并发 | 请求数 | 错误率 | P50 | P95 | P99 | 平均成本/题 |
|---:|---:|---:|---:|---:|---:|---:|
| 20 | 20 | 0% | 5.00s | 8.20s | 11.86s | ¥0.00619 |
| 50 | 50 | 0% | 5.62s | 8.26s | 8.84s | ¥0.00624 |

结论：20/50 并发均满足错误率 ≤1%、P95 ≤12s、成本 ≤¥0.02。压测脚本：`scripts/load_analytics.py`。

## 3. 告警

| 告警 | 条件（建议） | 级别 | 第一动作 |
|---|---|---|---|
| Analytics 5xx 高 | 5 分钟错误率 > 2% | P1 | 看 DB/模型依赖；必要时降级为澄清/拒绝 |
| P95 超 SLO | 5 分钟 P95 > 12s | P2 | 检查模型 429/超时、DB 慢查询、并发 |
| 越权 | `permission_violation > 0` | P0 | 立即查 audit、冻结 token、复核 RLS |
| PII 泄露 | `pii_leaks > 0` 或日志命中邮箱/手机号 | P0 | 停止出口、脱敏、审计、轮换密钥 |
| 审计缺口 | 入口请求数 - audit 行数 > 0 | P1 | 查 audit DB 写权限/连接 |
| 审批拒绝异常升高 | `status=rejected` 突增 | P2 | 查 EXPLAIN 阈值与查询模式 |
| 预算拒绝升高 | `status=budget` 突增 | P2 | 查 prompt/模型回归与循环 repair |
| plan 模式变慢/变贵 | P95 > 20s 或成本 > ¥0.02 | P2 | 检查步骤数/重复 SQL/repair；必要时退回 single |

## 4. 故障处理

### 4.1 Postgres / Analytics DB 不可用

1. `docker ps | grep agentlab-pg`；必要时 `bash scripts/start_analytics_db.sh`。
2. 检查只读角色：
   `docker exec agentlab-pg psql -U postgres -d agentlab -c "\du analytics_reader"`。
3. 检查 RLS 与授权：`analytics.customers_safe` 应 `security_invoker=true`；原始 `customers` 不给 name/email/phone。
4. API 应返回 503/500 而不是空答案；查 `/tmp/agentlab-demo-api.log` 与 `analytics_audit.status=error`。
5. 如果只是 audit 写库故障，查询仍可返回，但必须记录审计缺口并告警。

### 4.2 模型超时 / 429

1. 看 `analytics.model` span 与 `analytics_query status=error` 日志。
2. 429：降低并发、检查 DeepSeek 配额；不要用无限重试放大故障。
3. 超时：`ANALYTICS_MODEL_TIMEOUT` 默认 30s；必要时降低而不是提高，避免拖垮 P95。
4. 当前 `retry_async`/`CircuitBreaker` 已实现但默认图未接线；需要时在 API 层接入并做 A/B。

### 4.3 越权告警

1. 查 `analytics_audit` 最近 `permission`/`rejected` 记录；不要直接展开 question/sql 原文到聊天工具。
2. 确认请求 tenant 与 token tenant 不一致时 API 返回 403；查 `UserContext.tenant_id` 映射。
3. 复核 RLS policy 与 `SET LOCAL app.tenant_id`；必要时临时下线 Analytics 入口。
4. 轮换相关 token，记录事故时间线。

### 4.4 高成本 / 审批

1. `estimated_cost` 来自 `EXPLAIN (FORMAT JSON)`；阈值 `ANALYTICS_COST_THRESHOLD` 默认 100000。
2. 有 checkpointer/thread_id 时等待人工审批；没有时 fail-closed，返回“需要人工审批”。
3. 审批超时：不要自动批准；让请求失败并记录 audit `status=rejected`。
4. 标量子查询可能高估成本（实测 152k vs CTE 3.5k）；优先改写为 CTE/聚合，不要盲目提高阈值。

### 4.5 PII 告警

1. 确认 `redact_pii` 覆盖 answer、SQL、audit、SSE、日志、trace。
2. 查 `customers_safe` 是否被绕过；原始 `customers` 只允许列级 SELECT。
3. 清理已落地的 PII（日志轮转/审计脱敏），按安全流程上报。

### 4.6 Prompt / 模型回滚

1. 改 `ANALYTICS_PROMPT_<ID>_VERSION`（如 `ANALYTICS_PROMPT_UNDERSTAND_VERSION=v2`），重启 API/CLI。
2. 或修改 `configs/analytics/prompts/*.yaml` 的 `active`。
3. 回滚后跑 20 条 smoke：`bash scripts/ci_analytics.sh`。
4. 审计 `prompt_version/model_id` 字段确认新版本生效。

### 4.7 取消 / 断连

- API 取消：`POST /analytics/cancel {session_id}` 取消当前 asyncio task；流式收到 `error: cancelled`。
- SSE 断连：服务端停止迭代，尽力写 audit `status=cancelled`。
- 计划执行器取消：`cancel_task(request_id)` 阻止新步骤，已完成步骤保留结果。

## 5. 发布与回滚

- 评测顺序：`RUN_INTEGRATION=1` 的 seed 集成测试会把 analytics 数据重置到 `scale=0.01`；跑完必须执行
  `ANALYTICS_RESET=1 bash scripts/start_analytics_db.sh` 恢复 `scale=1.0`，再跑 50 条 eval/CI，否则 expected_result 全部错位。
- 发布前：`uv run pytest -q` + `bash scripts/ci_analytics.sh` + 50 条 eval。
- 发布后：观察 5 分钟错误率/P95/越权/PII/audit 缺口。
- 回滚：先回滚 prompt/model 版本；仍不恢复再回滚代码镜像/分支。
- 数据库迁移：`analytics_audit` 新列使用 `ADD COLUMN IF NOT EXISTS`，可重复执行。

## 6. 复盘模板

- 影响面：租户/请求数/时间窗口。
- 时间线：发现 → 止损 → 恢复 → 验证。
- 根因：模型/DB/权限/成本/前端。
- 数据：错误率、P95、成本、越权/PII/audit 缺口。
- 行动项：测试、告警、runbook、代码/配置。
