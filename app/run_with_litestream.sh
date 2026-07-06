#!/bin/sh
set -eu

DB_PATH="${DATABASE_PATH:-/app/data/recipes.db}"
DB_DIR="$(dirname "$DB_PATH")"

mkdir -p "$DB_DIR"

if [ "${LITESTREAM_ENABLED:-false}" = "true" ]; then
  if [ -s "$DB_PATH" ]; then
    echo "[litestream] enabled - local database already exists, skipping restore"
  else
    echo "[litestream] enabled - restoring database from S3 replica if available"
    # Restore only if a replica exists; otherwise keep local bootstrap flow.
    litestream restore -if-replica-exists -config /etc/litestream.yml "$DB_PATH"
  fi

  echo "[litestream] starting replication + app"
  python /app/app/seed_data.py
  exec litestream replicate -config /etc/litestream.yml -exec "python /app/app/app.py"
fi

echo "[litestream] disabled - starting app without replication"
exec sh -c "python /app/app/seed_data.py && python /app/app/app.py"
