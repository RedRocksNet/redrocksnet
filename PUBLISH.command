#!/bin/zsh
set -e

# Always run from this script's folder
cd "$(dirname "$0")"

echo "== RedRocksNet Publisher =="
echo "Working folder: $(pwd)"
echo ""

# 1) Generate gallery (if script exists)
if [ -f "./run_gallery.command" ]; then
  echo "-> Updating gallery..."
  chmod +x ./run_gallery.command
  ./run_gallery.command
elif [ -f "./generate_gallery.py" ]; then
  echo "-> Updating gallery (python)..."
  python3 ./generate_gallery.py
else
  echo "-> No gallery generator found, skip."
fi

# 2) Generate sutras (if script exists)
if [ -f "./run_sutras.command" ]; then
  echo "-> Updating sutras..."
  chmod +x ./run_sutras.command
  ./run_sutras.command
elif [ -f "./generate_sutras.py" ]; then
  echo "-> Updating sutras (python)..."
  python3 ./generate_sutras.py
else
  echo "-> No sutras generator found, skip."
fi

echo ""
echo "-> Git commit & push..."
git add -A
git status

# If nothing to commit, exit quietly
if git diff --cached --quiet; then
  echo "No changes to publish. Done."
  exit 0
fi

git commit -m "Publish update"
git push

echo ""
echo "✅ Published successfully!"
echo "You can close this window."
