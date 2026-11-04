#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python ml/train.py
.venv/bin/python ml/explain.py
.venv/bin/python ml/build_dashboard.py
.venv/bin/python ml/evaluate.py
.venv/bin/python ml/compare_models.py
.venv/bin/python ml/evaluate_rag.py
