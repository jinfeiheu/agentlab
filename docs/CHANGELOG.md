# Changelog

## 2026-11-26 — 多步计划执行（实验）

- `--plan` SQL-in-plan：规划器产出带 SQL 的 DAG，sqlguard 校验后由 `execute_plan` 并行执行。
- 单步失败尝试一次 repair；重复 SQL 去重；每步写 `analytics_audit_steps`。
- 10 条 smoke：task_success 0.9、P95 27.8s、¥0.0106/题；比 single 慢，不作为默认。
- GitHub Actions：离线 `uv sync --all-groups` + `pytest -q`。

## 2026-11-25 — Analytics Agent v1.0

- 多租户 Text-to-SQL 单 Agent：understand → clarify/refuse → plan_sql → validate_sql → estimate_cost → approve → execute → repair → answer。
- 三层 SQL 安全：sqlglot 只读守卫、`analytics_reader` 只读角色、PostgreSQL RLS；`customers_safe` + 列级授权 + PII 脱敏。
- 审计与成本：每次公共入口写 `analytics_audit`；`EXPLAIN` 成本守卫 + HITL fail-closed；请求级模型调用预算。
- 评测：50 条 golden（40 answer / 5 clarify / 5 refuse）、结果归一化、过程指标、9 类 failure class、badcase 回流、20 条 smoke CI 门禁。
- 多 Agent：Supervisor / Scout / SQL Analyst / Critic / Reporter，`Command(goto=...)`，`MAX_STEPS=6`，Critic fail-closed。
- A/B：single 1.000、multi 0.980、auto 1.000；multi 复杂子集无提升但 P95 +70%、步骤 3.5×、成本 +14.5%，默认 single。
- 版本与预算：YAML prompt registry、model router、rollback override、audit/trace 记录 `prompt_version` / `model_id`。
- API / CLI / 会话：`/analytics/chat`、SSE 计划事件、取消、四场景页面；`agentlab-analytics` CLI；多轮上下文复用与压缩。
- 压测与 SLO：20/50 并发 0% 错误、P95 8.2s、¥0.0062/题；runbook 与 Analytics 面试笔记。
- 最终验收：425 单测 + 27 集成通过；50 条 eval `task_success=1.0`、P95 8.31s、¥0.00561/题、越权 0、PII 0、audit 50/50。

## 2026-10-24 — RAG / Tool Agent 评测矩阵

- easy 27 条 + hard 100 条冻结评测；baseline / hybrid / hybrid+rerank；DeepSeek 与 qwen3.5:4b 跨模型对照。
- closed-book 消融；Token F1 / Exact Match；引用精度与上下文 precision/recall。
- hard 分类：单跳、多跳、时间/版本、歧义、表格/数值、不可回答。

## 2026-10-23 — MCP、记忆、多 Agent

- 两个 stdio/HTTP MCP server + client 聚合工具发现。
- 结构化长期记忆（profile / fact / preference / episode）与 TTL。
- Supervisor 多 Agent：researcher → writer → critic；`Command(goto=...)` 与 `MAX_STEPS=6`。

## 2026-10-22 — 服务化与安全

- FastAPI：JWT、限流、SSE 流式输出、HITL resume、健康检查。
- 输入注入检测、PII 脱敏、私有工单跨用户隔离。
- Postgres checkpoint / Store 持久化。

## 2026-10-21 — 检索与可观测

- pgvector 摄入、BM25 + 向量 + RRF 混合检索、cross-encoder rerank。
- OpenTelemetry / OpenInference → Phoenix trace。
- LLM-as-judge 与 easy golden 基线。

## 2026-10-20 — Baseline

- LangChain / LangGraph 单 Agent tool-calling 基线：retriever + calculator + send_report。
