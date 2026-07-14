#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

if [ ! -f "$REPO_ROOT/index.html" ] || [ ! -f "$REPO_ROOT/articles.html" ] || [ ! -f "$REPO_ROOT/generate_article.py" ] || [ ! -f "$REPO_ROOT/PUBLISH.command" ] || [ ! -f "$REPO_ROOT/CNAME" ]; then
  echo "ERROR: This does not look like the redrocks.net repository."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found."
  exit 1
fi

echo "RedRocks Publisher"
echo "Repository: $REPO_ROOT"
echo "Local address: http://127.0.0.1:8765"
echo "This tool is available only on this Mac."
echo "Press Control-C to stop."
echo

if lsof -ti tcp:8765 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Publisher is already running on 127.0.0.1:8765."
  open "http://127.0.0.1:8765"
  exit 0
fi

python3 "$REPO_ROOT/publisher/app.py" &
SERVER_PID=$!
sleep 1
open "http://127.0.0.1:8765"
wait "$SERVER_PID"
