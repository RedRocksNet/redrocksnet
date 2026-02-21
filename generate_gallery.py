import os
import re
import html
from datetime import datetime

# ====== Config ======
IMAGE_ROOT = "images"          # images/<album>/*.jpg
GALLERY_INDEX = "gallery.html" # 画廊列表页
GALLERY_DIR = "gallery"        # 子画廊页面目录 gallery/<album>.html

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp")

# ====== Helpers ======
def slugify(name: str) -> str:
    """Make a safe filename slug from folder name."""
    s = name.strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^A-Za-z0-9\-_]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "album"

def is_image_file(fn: str) -> bool:
    return fn.lower().endswith(IMAGE_EXTS)

def list_images_in_folder(folder_path: str):
    """Return sorted image filenames (not including subfolders)."""
    try:
        files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and is_image_file(f)]
    except FileNotFoundError:
        return []
    return sorted(files)  # 按文件名升序（稳定）

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def read_album_folders():
    """Return album folder names under images/ (only directories, excluding hidden)."""
    if not os.path.isdir(IMAGE_ROOT):
        return []
    albums = []
    for name in os.listdir(IMAGE_ROOT):
        if name.startswith("."):
            continue
        full = os.path.join(IMAGE_ROOT, name)
        if os.path.isdir(full):
            albums.append(name)
    # A：按文件夹名倒序（最新在最前）
    albums.sort(reverse=True)
    return albums

# ====== HTML Templates ======
BASE_STYLE = """
    body { font-family: Arial, sans-serif; margin: 0; padding: 0; text-align: center; background: #f5f5f5; }
    header { background: #222; color: #fff; padding: 15px; }
    h1 { margin: 0; }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 20px; }
    .grid { display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; }
    .card { width: 280px; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,.08); text-align: left; }
    .card a { color: inherit; text-decoration: none; display: block; }
    .thumb { width: 100%; height: 190px; background: #ddd; display:flex; align-items:center; justify-content:center; overflow:hidden; }
    .thumb img { width: 100%; height: 100%; object-fit: cover; display:block; }
    .meta { padding: 12px 14px; }
    .title { font-weight: 700; font-size: 16px; margin: 0 0 6px 0; }
    .count { font-size: 13px; opacity: .7; margin: 0; }
    footer { margin: 40px 0; font-size: 14px; color: #555; }
    .back { display:inline-block; margin: 12px 0 0 0; color: #fff; text-decoration: none; opacity: .85; }
    .back:hover { opacity: 1; }
    .photos { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; padding: 20px; }
    .photos img { width: 100%; height: auto; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,.08); }
    .crumb { text-align:left; max-width:1200px; margin:0 auto; padding: 14px 20px 0 20px; }
    .crumb a { color:#0b62d6; text-decoration:none; }
    .crumb a:hover { text-decoration:underline; }
"""

def build_gallery_index(albums, root_images):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cards = []

    # 先放“子画廊”
    for folder in albums:
        imgs = list_images_in_folder(os.path.join(IMAGE_ROOT, folder))
        if not imgs:
            continue
        cover = imgs[0]  # 封面：该文件夹排序后的第一张（稳定）
        slug = slugify(folder)
        href = f"gallery/{slug}.html"
        cover_src = f"{IMAGE_ROOT}/{folder}/{cover}"

        cards.append(f"""
        <div class="card">
          <a href="{href}">
            <div class="thumb"><img src="{cover_src}" alt="{html.escape(folder)}"></div>
            <div class="meta">
              <p class="title">{html.escape(folder)}</p>
              <p class="count">{len(imgs)} photos</p>
            </div>
          </a>
        </div>
        """)

    # 如果 images/ 根目录也有散图（可选：给你一个 “Unsorted”）
    if root_images:
        cover = root_images[0]
        href = f"gallery/_unsorted.html"
        cover_src = f"{IMAGE_ROOT}/{cover}"
        cards.insert(0, f"""
        <div class="card">
          <a href="{href}">
            <div class="thumb"><img src="{cover_src}" alt="Unsorted"></div>
            <div class="meta">
              <p class="title">Unsorted</p>
              <p class="count">{len(root_images)} photos</p>
            </div>
          </a>
        </div>
        """)

    html_text = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Gallery</title>
  <style>{BASE_STYLE}</style>
</head>
<body>
<header>
  <h1>Gallery</h1>
  <a class="back" href="index.html">← Back to Home</a>
</header>

<div class="wrap">
  <div class="grid">
    {''.join(cards) if cards else '<p>No albums found in images/</p>'}
  </div>
</div>

<footer>Last updated: {now}</footer>
</body>
</html>
"""
    with open(GALLERY_INDEX, "w", encoding="utf-8") as f:
        f.write(html_text)

def build_album_page(album_name, album_images, album_slug):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    # 子画廊页在 /gallery/ 下，所以图片路径需要 ../images/...
    imgs_html = "\n".join([f'<img src="../{IMAGE_ROOT}/{album_name}/{img}" alt="{html.escape(img)}">' for img in album_images])

    text = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(album_name)}</title>
  <style>{BASE_STYLE}</style>
</head>
<body>
<header>
  <h1>{html.escape(album_name)}</h1>
  <a class="back" href="../{GALLERY_INDEX}">← Back to Gallery</a>
</header>

<div class="crumb"><a href="../{GALLERY_INDEX}">Gallery</a> / {html.escape(album_name)}</div>

<div class="photos">
{imgs_html}
</div>

<footer>Last updated: {now}</footer>
</body>
</html>
"""
    out_path = os.path.join(GALLERY_DIR, f"{album_slug}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)

def build_unsorted_page(root_images):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    imgs_html = "\n".join([f'<img src="../{IMAGE_ROOT}/{img}" alt="{html.escape(img)}">' for img in root_images])

    text = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Unsorted</title>
  <style>{BASE_STYLE}</style>
</head>
<body>
<header>
  <h1>Unsorted</h1>
  <a class="back" href="../{GALLERY_INDEX}">← Back to Gallery</a>
</header>

<div class="crumb"><a href="../{GALLERY_INDEX}">Gallery</a> / Unsorted</div>

<div class="photos">
{imgs_html}
</div>

<footer>Last updated: {now}</footer>
</body>
</html>
"""
    out_path = os.path.join(GALLERY_DIR, "_unsorted.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)

def cleanup_stale_album_pages(keep_filenames):
    """Delete old gallery/*.html that are no longer generated."""
    if not os.path.isdir(GALLERY_DIR):
        return
    for fn in os.listdir(GALLERY_DIR):
        if not fn.lower().endswith(".html"):
            continue
        if fn not in keep_filenames:
            try:
                os.remove(os.path.join(GALLERY_DIR, fn))
            except Exception:
                pass

# ====== Main ======
if __name__ == "__main__":
    print("⏳ 正在生成 gallery（子画廊模式）...")

    ensure_dir(GALLERY_DIR)

    albums = read_album_folders()

    # 根目录散图（可选）
    root_images = list_images_in_folder(IMAGE_ROOT)

    # 生成子画廊页
    keep_pages = set()

    for folder in albums:
        imgs = list_images_in_folder(os.path.join(IMAGE_ROOT, folder))
        if not imgs:
            continue
        slug = slugify(folder)
        build_album_page(folder, imgs, slug)
        keep_pages.add(f"{slug}.html")

    # 生成 Unsorted（如果有根目录散图）
    if root_images:
        build_unsorted_page(root_images)
        keep_pages.add("_unsorted.html")

    # 清理被删掉的相册页面
    cleanup_stale_album_pages(keep_pages)

    # 生成 gallery.html（相册列表）
    build_gallery_index(albums, root_images)

    print("✅ gallery.html + 子画廊页面已更新！")
