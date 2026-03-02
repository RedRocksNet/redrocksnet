#!/bin/bash
set -e

echo "== RedRocksNet Publisher =="

WORKDIR="$(cd "$(dirname "$0")" && pwd)"
cd "$WORKDIR"
echo "Working folder: $WORKDIR"
echo

# =========================
# Stage 0: Preflight resize (JPG only, in-place, long edge <= 2000)
# =========================
MAX_SIZE=2000
JPEG_QUALITY=90
MAKE_BACKUP=1   # 1 = keep a .orig backup beside the file the first time we resize it; 0 = no backup

# If this folder is a git repo, use repo root; otherwise just use WORKDIR
if git_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  ROOT="$git_root"
else
  ROOT="$WORKDIR"
fi

IMAGES_DIR="$ROOT/images"

if [ ! -d "$IMAGES_DIR" ]; then
  echo "⚠️  Preflight: images folder not found at: $IMAGES_DIR"
  echo "    Skipping resize stage."
  echo
else
  echo "🔎 Preflight: scanning JPG/JPEG under:"
  echo "    $IMAGES_DIR"
  echo "    Rule: long edge <= ${MAX_SIZE}px (resize down if larger)"
  echo

  if ! command -v sips >/dev/null 2>&1; then
    echo "❌ 'sips' not found (unexpected on macOS). Cannot resize."
    exit 1
  fi

  resized_count=0
  scanned_count=0

  # Recursively find JPG/JPEG, safe with spaces (null-delimited)
  while IFS= read -r -d '' f; do
    scanned_count=$((scanned_count+1))

    # Read dimensions
    w="$(sips -g pixelWidth  "$f" 2>/dev/null | awk '/pixelWidth/  {print $2}')"
    h="$(sips -g pixelHeight "$f" 2>/dev/null | awk '/pixelHeight/ {print $2}')"

    # If we couldn't read dimensions, skip
    if [[ -z "$w" || -z "$h" ]]; then
      echo "⚠️  Skip (cannot read size): ${f#$ROOT/}"
      continue
    fi

    # Determine long edge
    if (( w >= h )); then
      long="$w"
    else
      long="$h"
    fi

    if (( long > MAX_SIZE )); then
      echo "↘️  Resize: ${f#$ROOT/}  (${w}x${h} -> long=${MAX_SIZE})"

      # optional one-time backup
      if (( MAKE_BACKUP == 1 )) && [ ! -f "${f}.orig" ]; then
        cp -p "$f" "${f}.orig"
      fi

      # Write to temp then atomic replace
      tmp="${f}.tmp_resize.jpg"
      rm -f "$tmp"

      # -Z sets max dimension; --out writes new file
      sips -Z "$MAX_SIZE" "$f" --out "$tmp" >/dev/null

      # Optional: enforce JPEG quality using ImageMagick if available
      if command -v magick >/dev/null 2>&1; then
        tmp2="${f}.tmp_resize_q.jpg"
        rm -f "$tmp2"
        magick "$tmp" -quality "$JPEG_QUALITY" "$tmp2"
        mv -f "$tmp2" "$tmp"
      fi

      mv -f "$tmp" "$f"
      resized_count=$((resized_count+1))
    fi
  done < <(find "$IMAGES_DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) -print0)

  echo
  echo "✅ Preflight done: scanned ${scanned_count}, resized ${resized_count}."
  echo
fi
# =========================
# End Stage 0
# =========================

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