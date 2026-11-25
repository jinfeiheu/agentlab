#!/usr/bin/env bash
# Agent Interview Lab 演示脚本。可重复执行。
# 默认在调用 DeepSeek 前询问；非交互环境或 DEMO_AUTO!=1 时跳过付费步骤。
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

API_PORT=${DEMO_API_PORT:-8010}
step() {
  printf '\n============================================================\n'
  printf '== %s\n' "$1"
  printf '%s\n' "$2"
  printf '============================================================\n'
}

confirm() {
  if [ "${DEMO_AUTO:-0}" = "1" ]; then
    return 0
  fi
  if [ ! -t 0 ]; then
    echo "非交互环境：跳过需要 DeepSeek 的步骤（设置 DEMO_AUTO=1 可强制执行）。"
    return 1
  fi
  read -r -p "$1 [y/N] " answer
  [[ "$answer" =~ ^[Yy]$ ]]
}

step "1/9 检查环境" \
  "需要 uv、Docker、Ollama 和 .env 中的 DEEPSEEK_API_KEY。"

command -v uv >/dev/null || { echo "缺少 uv，请先安装：https://docs.astral.sh/uv/"; exit 1; }
command -v docker >/dev/null || { echo "缺少 docker，请先安装并启动 Docker。"; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker 未运行，请先启动 Docker。"; exit 1; }
curl -s -m 3 http://localhost:11434/api/tags >/dev/null \
  || { echo "Ollama 不可用，请先运行：ollama serve"; exit 1; }

if [ ! -f .env ]; then
  cp .env.example .env
  echo "已创建 .env；请填入 DEEPSEEK_API_KEY 后重新运行。"
  exit 1
fi

KEY_OK=0
if [ -n "${DEEPSEEK_API_KEY:-}" ] && [ "$DEEPSEEK_API_KEY" != "sk-your-key-here" ]; then
  KEY_OK=1
elif grep -Eq '^DEEPSEEK_API_KEY=.+' .env && ! grep -q '^DEEPSEEK_API_KEY=sk-your-key-here' .env; then
  KEY_OK=1
fi
if [ "$KEY_OK" = "0" ]; then
  echo "提示：.env 里还没有真实 DEEPSEEK_API_KEY；离线测试仍会运行，付费步骤会跳过。"
fi

step "2/9 安装依赖" \
  "uv sync --all-groups：安装基础依赖和 dev/serve/rag/mcp/observability 组。"
uv sync --all-groups

step "3/9 离线测试" \
  "uv run pytest -q：不依赖 DeepSeek / Ollama / Postgres 的离线测试。"
uv run pytest -q

step "4/9 启动 Postgres" \
  "bash scripts/start_db.sh：启动/复用 pgvector 容器，创建 vector 扩展并写入 demo 工单。"
bash scripts/start_db.sh

step "5/9 摄入语料" \
  "easy：data/docs -> docs(54 chunks)；hard：data/docs_hard -> docs_hard(66 chunks)。"
uv run python -m agentlab.rag.ingest --reset
uv run python -m agentlab.rag.ingest --docs-dir data/docs_hard --collection docs_hard --reset

step "6/9 快速评测" \
  "跑 3 条 hard 问题，验证检索、judge、分层报告和成本统计；会调用 DeepSeek。"
if [ "$KEY_OK" = "1" ] && confirm "运行 3 条 hard 评测（会产生少量 DeepSeek 费用）?"; then
  uv run python -m eval.run_eval --corpus hard --limit 3 \
    --output eval/results/demo-hard-smoke.md
else
  echo "跳过。手动运行：uv run python -m eval.run_eval --corpus hard --limit 3"
fi

step "7/9 MCP 工具发现" \
  "启动两个 stdio MCP server，聚合 search_docs/list_sources/doc_stats/calculator/word_count。"
timeout 120 uv run python -m agentlab.mcp.client

step "8/9 Supervisor 多 Agent CLI" \
  "自动输入一个问题后退出：观察 supervisor -> researcher -> writer -> critic 的路由。"
if [ "$KEY_OK" = "1" ] && confirm "运行一次多 Agent 问答（会调用 DeepSeek）?"; then
  printf 'checkpointer 是什么？\n/quit\n' \
    | timeout 300 uv run agentlab --multi --user alice
else
  echo "跳过。手动运行：uv run agentlab --multi --user alice"
fi

step "9/9 启动 API 并检查健康" \
  "USE_DB=true 使用 Postgres checkpointer/Store；健康检查通过后打印网页地址。"
if [ "$KEY_OK" = "1" ]; then
  USE_DB=true uv run uvicorn agentlab.api.app:app --host 127.0.0.1 --port "$API_PORT" \
    > /tmp/agentlab-demo-api.log 2>&1 &
  API_PID=$!
  trap 'kill "$API_PID" 2>/dev/null || true' EXIT INT TERM
  if curl -s --retry 30 --retry-delay 1 --retry-connrefused \
      "http://127.0.0.1:$API_PORT/healthz" >/dev/null; then
    echo "API 已启动：http://127.0.0.1:$API_PORT"
    echo "用 alice / alice-pass 登录；会话 ID 由页面自动生成。"
    echo "日志：/tmp/agentlab-demo-api.log"
    echo "API 会在演示脚本退出时停止；要长期运行请手动执行："
    echo "  USE_DB=true uv run uvicorn agentlab.api.app:app --host 0.0.0.0 --port 8000"
  else
    echo "API 没有在预期时间内就绪，查看 /tmp/agentlab-demo-api.log"
    exit 1
  fi
else
  echo "跳过。手动运行：USE_DB=true uv run uvicorn agentlab.api.app:app --host 0.0.0.0 --port 8000"
fi

printf '\n演示完成。\n'
printf '更多命令：\n'
printf '  CLI:        uv run agentlab [--simple|--multi --user alice]\n'
printf '  Phoenix:    bash scripts/start_phoenix.sh  (另开终端)\n'
printf '  评测矩阵:   uv run python -m eval.run_eval --corpus hard --retriever hybrid --rerank\n'
printf '  MCP HTTP:   uv run python -m agentlab.mcp.knowledge_server --transport streamable-http --port 8811\n'
printf '  Analytics:  bash scripts/demo_analytics.sh\n'
