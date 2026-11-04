#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d frontend/dist ]; then
  echo "→ Building frontend once"
  (cd frontend && pnpm install --frozen-lockfile && pnpm build)
fi
exec .venv/bin/python -m uvicorn backend.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
