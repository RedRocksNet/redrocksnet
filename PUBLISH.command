#!/bin/bash
set -e

echo "== RedRocksNet Publisher =="

WORKDIR="$(cd "$(dirname "$0")" && pwd)"
cd "$WORKDIR"
echo "Working folder: $WORKDIR"
echo

# =========================
# Stage 0: Preflight resize (site images, in-place, long edge <= 2000)
# =========================
MAX_SIZE=2000
JPEG_QUALITY=90

# If this folder is a git repo, use repo root; otherwise just use WORKDIR
if git_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  ROOT="$git_root"
else
  ROOT="$WORKDIR"
fi

IMAGES_DIR="$ROOT/images"
ARTICLES_DIR="$ROOT/articles"

if ! command -v sips >/dev/null 2>&1; then
  echo "❌ 'sips' not found (unexpected on macOS). Cannot resize."
  exit 1
fi

resized_count=0
scanned_count=0

resize_tree() {
  local scan_dir="$1"
  local label="$2"
  [ -d "$scan_dir" ] || return 0

  echo "🔎 Preflight: scanning ${label}:"
  echo "    $scan_dir"
  echo "    Rule: long edge <= ${MAX_SIZE}px (resize down if larger)"

  while IFS= read -r -d '' f; do
    scanned_count=$((scanned_count+1))
    w="$(sips -g pixelWidth  "$f" 2>/dev/null | awk '/pixelWidth/  {print $2}')"
    h="$(sips -g pixelHeight "$f" 2>/dev/null | awk '/pixelHeight/ {print $2}')"

    if [[ -z "$w" || -z "$h" ]]; then
      echo "⚠️  Skip (cannot read size): ${f#$ROOT/}"
      continue
    fi

    if (( w >= h )); then long="$w"; else long="$h"; fi

    if (( long > MAX_SIZE )); then
      echo "↘️  Resize: ${f#$ROOT/}  (${w}x${h} -> long=${MAX_SIZE})"
      ext="${f##*.}"
      tmp="${f}.tmp_resize.${ext}"
      rm -f "$tmp"
      sips -Z "$MAX_SIZE" "$f" --out "$tmp" >/dev/null

      # Recompress JPEGs when ImageMagick is available; keep PNG format unchanged.
      ext_lower="$(printf '%s' "$ext" | tr '[:upper:]' '[:lower:]')"
      if command -v magick >/dev/null 2>&1 && [[ "$ext_lower" == "jpg" || "$ext_lower" == "jpeg" ]]; then
        tmp2="${f}.tmp_resize_q.${ext}"
        rm -f "$tmp2"
        magick "$tmp" -quality "$JPEG_QUALITY" "$tmp2"
        mv -f "$tmp2" "$tmp"
      fi

      mv -f "$tmp" "$f"
      resized_count=$((resized_count+1))
    fi
  done < <(find "$scan_dir" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) -print0)
}

resize_tree "$IMAGES_DIR" "JPG/JPEG/PNG under images"
resize_tree "$ARTICLES_DIR" "JPG/JPEG/PNG under articles"

echo
echo "✅ Preflight done: scanned ${scanned_count}, resized ${resized_count}."
echo
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

echo "-> Updating sitemap..."
python3 generate_sitemap.py
echo "✅ sitemap.xml generated"
echo

echo "-> Git commit & push..."
git add .
git status

push_and_verify() {
  git push
  if ! git diff --quiet HEAD @{u}; then
    echo "❌ Push verification failed: local HEAD and upstream are still different."
    echo "   Please check network/authentication and run this publisher again."
    exit 1
  fi
  echo "✅ Published successfully!"
}

if git diff --cached --quiet; then
  echo "ℹ️ No new changes to commit."
  if git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1; then
    if git rev-list --count @{u}..HEAD | grep -qv '^0$'; then
      echo "-> Found local commits not yet pushed. Pushing now..."
      push_and_verify
    else
      echo "✅ Already up to date with upstream."
    fi
  else
    echo "⚠️ No upstream branch configured; skipping push verification."
  fi
else
  git commit -m "Publish update"
  push_and_verify
fi
