#!/usr/bin/env bash
# Analytics CI 门禁：全量单测 + 20 条 smoke eval + 回归/越权/PII 阈值。
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
BASELINE="$ROOT_DIR/eval/analytics_smoke_baseline.json"
REPORT="$ROOT_DIR/eval/results/analytics-smoke.json"
BADCASES="$ROOT_DIR/eval/results/analytics-badcases.json"

cd "$ROOT_DIR"

echo "[1/2] 单元测试"
uv run pytest -q

echo "[2/2] Smoke eval + 门禁"
# 评测关注回答质量，不让 EXPLAIN 成本守卫把合法昂贵查询挡掉；
# 成本守卫本身由 tests/test_analytics_reliability.py 覆盖。
uv run python -m eval.run_analytics_eval \
  --smoke \
  --auto-approve \
  --baseline "$BASELINE" \
  --output "$REPORT" \
  --badcases "$BADCASES"

echo "CI 门禁通过；报告：$REPORT"
