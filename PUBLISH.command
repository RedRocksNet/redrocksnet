#!/bin/bash
set -e

echo "== RedRocksNet Publisher =="

WORKDIR="$(cd "$(dirname "$0")" && pwd)"
cd "$WORKDIR"
echo "Working folder: $WORKDIR"
echo

# Make sure scripts run in repo root
# Optional but strongly recommended to prevent overwriting remote changes:
# git pull --rebase

echo "-> Updating banner..."
python3 generate_banner.py
echo "✅ banner_list.js generated"
echo

echo "-> Updating gallery..."
python3 generate_gallery.py
echo "✅ gallery pages generated"
echo

echo "-> Updating sutras..."
python3 generate_sutras.py
echo "✅ sutras.html generated"
echo

echo "-> Updating articles..."
python3 generate_article.py
echo "✅ articles pages generated"
echo

echo "-> Git commit & push..."
git add .
git status

if git diff --cached --quiet; then
  echo "ℹ️ No changes to commit."
else
  git commit -m "Publish update"
  git push
  echo "✅ Published successfully!"
fi