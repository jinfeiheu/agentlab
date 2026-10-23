#!/usr/bin/env bash
# 启动或复用本地 pgvector 容器,并初始化演示数据。可重复执行。
set -euo pipefail

NAME=agentlab-pg
IMAGE=docker.m.daocloud.io/pgvector/pgvector:pg16
PORT=5432
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

if docker inspect "$NAME" >/dev/null 2>&1; then
  if [ "$(docker inspect -f '{{.State.Running}}' "$NAME")" = "true" ]; then
    echo "容器 $NAME 已在运行"
  else
    echo "启动已有容器 $NAME"
    docker start "$NAME" >/dev/null
  fi
else
  echo "创建容器 $NAME"
  docker run -d --name "$NAME" \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB=agentlab \
    -p "$PORT:5432" \
    "$IMAGE" >/dev/null
fi

echo "等待 Postgres 就绪..."
for _ in $(seq 1 60); do
  if docker exec "$NAME" pg_isready -U postgres -d agentlab >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker exec "$NAME" pg_isready -U postgres -d agentlab >/dev/null

echo "创建 vector 扩展并写入演示数据"
docker exec "$NAME" psql -U postgres -d agentlab -v ON_ERROR_STOP=1 \
  -c "CREATE EXTENSION IF NOT EXISTS vector;" >/dev/null
docker exec -i "$NAME" psql -U postgres -d agentlab -v ON_ERROR_STOP=1 \
  < "$SCRIPT_DIR/seed_demo.sql" >/dev/null

echo "Postgres 就绪: postgresql://postgres:postgres@localhost:$PORT/agentlab"
