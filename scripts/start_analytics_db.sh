#!/usr/bin/env bash
# 启动/复用 Postgres，创建 analytics 只读角色并灌入合成数据。可重复执行。
set -euo pipefail

NAME=agentlab-pg
DB=agentlab
READER=analytics_reader
READER_PASSWORD=analytics_reader
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
SCALE="${ANALYTICS_SEED_SCALE:-1.0}"
RESET="${ANALYTICS_RESET:-0}"

"$SCRIPT_DIR/start_db.sh"

echo "创建/更新只读角色 $READER"
docker exec -i "$NAME" psql -U postgres -d "$DB" -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$READER') THEN
    CREATE ROLE $READER LOGIN PASSWORD '$READER_PASSWORD'
      NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  ELSE
    ALTER ROLE $READER WITH LOGIN PASSWORD '$READER_PASSWORD'
      NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END
\$\$;

ALTER ROLE $READER SET default_transaction_read_only = on;
ALTER ROLE $READER SET search_path TO analytics, public;
GRANT CONNECT ON DATABASE $DB TO $READER;
REVOKE ALL ON SCHEMA public FROM $READER;
SQL

echo "生成 analytics 合成数据（scale=$SCALE, reset=$RESET）"
cd "$ROOT_DIR"
if [ "$RESET" = "1" ]; then
  uv run python -m agentlab.analytics.seed --reset --scale "$SCALE"
else
  uv run python -m agentlab.analytics.seed --scale "$SCALE"
fi

echo "授予只读权限"
docker exec -i "$NAME" psql -U postgres -d "$DB" -v ON_ERROR_STOP=1 <<SQL
GRANT USAGE ON SCHEMA analytics TO $READER;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO $READER;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics
  GRANT SELECT ON TABLES TO $READER;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
  ON ALL TABLES IN SCHEMA analytics FROM $READER;
SQL

echo "Analytics DB 就绪："
echo "  postgresql://$READER:$READER_PASSWORD@localhost:5432/$DB"
