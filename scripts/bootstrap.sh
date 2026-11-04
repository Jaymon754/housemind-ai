#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON=${PYTHON:-python3.13}
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  PYTHON=python3
fi
echo "→ Python: $($PYTHON --version)"
if [ ! -d .venv ]; then
  "$PYTHON" -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r backend/requirements.txt

if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm not found. Install Node 20+ and run: npm install -g pnpm"
  exit 1
fi
(cd frontend && pnpm install)
cp -n .env.example .env || true
echo "✓ Dependencies installed. Edit .env if you have model API keys."
