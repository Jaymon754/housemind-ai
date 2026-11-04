#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -n "${CHROME:-}" ]; then
  BROWSER="$CHROME"
elif [ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
  BROWSER="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
elif command -v google-chrome >/dev/null 2>&1; then
  BROWSER="google-chrome"
elif command -v chromium >/dev/null 2>&1; then
  BROWSER="chromium"
else
  echo "Chrome/Chromium not found. Set CHROME=/path/to/chrome" >&2
  exit 1
fi

PROFILE=$(mktemp -d)
trap 'rm -rf "$PROFILE"' EXIT
"$BROWSER" \
  --headless=new --disable-gpu --no-sandbox \
  --user-data-dir="$PROFILE" \
  --allow-file-access-from-files \
  --no-pdf-header-footer \
  --print-to-pdf="docs/HouseMind_AI_技术文档.pdf" \
  --virtual-time-budget=6000 \
  "file://$PWD/docs/technical_doc.html"
echo "✓ wrote docs/HouseMind_AI_技术文档.pdf"
