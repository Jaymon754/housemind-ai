#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  echo "Run scripts/bootstrap.sh first" >&2
  exit 1
fi
trap 'kill 0' INT TERM EXIT
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload &
(cd frontend && pnpm dev) &
wait
