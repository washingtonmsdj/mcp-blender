#!/usr/bin/env bash
set -euo pipefail

WRANGLER_VERSION="${WRANGLER_VERSION:-4.141.0}"
DB_NAME="${ORDAX_CLOUDFLARE_D1_NAME:-ordax-control-plane-v3}"
BUCKET_NAME="${ORDAX_CLOUDFLARE_R2_BUCKET:-ordax-device-artifacts}"
WORKER_NAME="${ORDAX_CLOUDFLARE_WORKER_NAME:-ordax-control-plane-v3}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLOUDFLARE_DIR="$ROOT/control-plane/cloudflare"
GENERATED_CONFIG="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/ordax-wrangler.generated.jsonc"

: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN is required}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID is required}"
: "${ORDAX_OPERATOR_TOKEN:?ORDAX_OPERATOR_TOKEN is required}"

wrangler() {
  npx --yes "wrangler@${WRANGLER_VERSION}" "$@"
}

echo "Resolving D1 database: ${DB_NAME}"
d1_json="$(wrangler d1 list --json)"
db_id="$(printf '%s' "$d1_json" | python -c '
import json,sys
name=sys.argv[1]
rows=json.load(sys.stdin)
for row in rows:
    if row.get("name") == name:
        print(row.get("uuid") or row.get("id") or "")
        break
' "$DB_NAME")"

if [[ -z "$db_id" ]]; then
  echo "Creating D1 database: ${DB_NAME}"
  wrangler d1 create "$DB_NAME"
  d1_json="$(wrangler d1 list --json)"
  db_id="$(printf '%s' "$d1_json" | python -c '
import json,sys
name=sys.argv[1]
rows=json.load(sys.stdin)
for row in rows:
    if row.get("name") == name:
        print(row.get("uuid") or row.get("id") or "")
        break
' "$DB_NAME")"
fi

if [[ ! "$db_id" =~ ^[0-9a-fA-F-]{32,36}$ ]]; then
  echo "Could not resolve D1 database id for ${DB_NAME}" >&2
  exit 2
fi

echo "Resolving R2 bucket: ${BUCKET_NAME}"
if ! wrangler r2 bucket info "$BUCKET_NAME" --json >/dev/null 2>&1; then
  echo "Creating R2 bucket: ${BUCKET_NAME}"
  wrangler r2 bucket create "$BUCKET_NAME"
fi

python - "$GENERATED_CONFIG" "$WORKER_NAME" "$db_id" "$DB_NAME" "$BUCKET_NAME" "$CLOUDFLARE_DIR" <<'PY'
from __future__ import annotations
import json
import sys
from pathlib import Path

target = Path(sys.argv[1])
worker_name, db_id, db_name, bucket_name, cloudflare_dir = sys.argv[2:]
config = {
    "name": worker_name,
    "main": str(Path(cloudflare_dir) / "src" / "index.ts"),
    "compatibility_date": "2026-09-27",
    "observability": {"enabled": True},
    "d1_databases": [{
        "binding": "DB",
        "database_name": db_name,
        "database_id": db_id,
        "migrations_dir": str(Path(cloudflare_dir) / "migrations"),
    }],
    "r2_buckets": [{
        "binding": "ARTIFACTS",
        "bucket_name": bucket_name,
    }],
    "durable_objects": {
        "bindings": [{
            "name": "DEVICE_SESSIONS",
            "class_name": "DeviceSession",
        }],
    },
    "migrations": [{
        "tag": "v1",
        "new_sqlite_classes": ["DeviceSession"],
    }],
}
target.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
print(target)
PY

echo "Applying D1 migrations"
wrangler d1 migrations apply DB --remote --config "$GENERATED_CONFIG"

echo "Updating Worker operator secret"
printf '%s' "$ORDAX_OPERATOR_TOKEN" | wrangler secret put ORDAX_OPERATOR_TOKEN --config "$GENERATED_CONFIG"

echo "Deploying ${WORKER_NAME}"
wrangler deploy --config "$GENERATED_CONFIG"

echo "Cloudflare v3 deployment complete."
echo "D1=${DB_NAME}"
echo "R2=${BUCKET_NAME}"
echo "WORKER=${WORKER_NAME}"
