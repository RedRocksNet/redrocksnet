#!/bin/bash
set -e

echo "== RedRocksNet Publisher =="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Working folder: $SCRIPT_DIR"
cd "$SCRIPT_DIR"

# --- Generate gallery ---
echo ""
echo "-> Updating gallery..."
if [ -f "./run_gallery.command" ]; then
  bash ./run_gallery.command
else
  python3 ./generate_gallery.py
fi

# --- Generate sutras ---
echo ""
echo "-> Updating sutras..."
if [ -f "./run_sutras.command" ]; then
  bash ./run_sutras.command
else
  python3 ./generate_sutras.py
fi

# --- Generate articles ---
echo ""
echo "-> Updating articles..."
if [ -f "./run_article.command" ]; then
  bash ./run_article.command
else
  if [ -f "./generate_article.py" ]; then
    python3 ./generate_article.py
  else
    echo "⚠️ generate_article.py not found, skip."
  fi
fi

# --- Git commit & push (only once) ---
echo ""
echo "-> Git commit & push..."
git add -A

if git diff --cached --quiet; then
  echo "✅ No changes to commit."
  exit 0
fi

git commit -m "Publish update"
git push

echo ""
echo "✅ Published successfully!"
echo "You can close this window."