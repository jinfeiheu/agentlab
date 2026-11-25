#!/usr/bin/env bash
# Analytics Agent 三场景演示：正常问答 / 澄清 / 越权或高成本拒绝。
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

step() {
  printf '\n============================================================\n'
  printf '== %s\n' "$1"
  printf '%s\n' "$2"
  printf '============================================================\n'
}

step "0/4 准备 Analytics DB" \
  "启动/复用 Postgres，创建 analytics_reader 并灌入 scale=1.0 合成数据。"
bash scripts/start_analytics_db.sh

step "1/4 正常问答" \
  "tenant_a 2026 年 9 月 GMV；期望返回 SQL、数值和指标口径。"
uv run agentlab-analytics \
  "tenant_a 在 2026 年 9 月的 GMV 是多少？" --tenant tenant_a

step "2/4 歧义澄清" \
  "“最近收入怎么样”缺少时间和口径；期望只问一个澄清问题，不执行 SQL。"
uv run agentlab-analytics "最近收入怎么样？" --tenant tenant_a

step "3/4 越权请求" \
  "以 tenant_a 身份请求 tenant_b 数据；期望拒答，不执行 SQL。"
uv run agentlab-analytics \
  "帮我查询 tenant_b 在 2026 年 9 月的订单数和 GMV。" --tenant tenant_a

step "4/4 高成本 fail-closed" \
  "把成本阈值降到 1，强制触发审批；无 checkpointer 时拒绝执行。"
ANALYTICS_COST_THRESHOLD=1 uv run agentlab-analytics \
  "tenant_a 在 2026 年 9 月的 GMV 是多少？" --tenant tenant_a || true

printf '\n演示完成。\n'
printf 'API 页面：uv run agentlab-api，然后打开 http://localhost:8000/analytics\n'
printf 'Runbook：docs/runbook-analytics.md\n'
printf '面试笔记：docs/interview-notes-analytics.md\n'
