import os

IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
IMAGE_FOLDER = "images"
OUTPUT_FILE = "gallery.html"

def get_image_files():
    return sorted([
        f for f in os.listdir(IMAGE_FOLDER)
        if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
    ])

def generate_html(images):
    html = """<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <title>摄影作品</title>
  <style>
    body { margin: 0; font-family: sans-serif; background-color: #111; color: #fff; }
    nav { background: #222; padding: 1rem; text-align: center; position: fixed; width: 100%; top: 0; z-index: 1000; }
    nav a { color: #fff; margin: 0 1rem; text-decoration: none; font-weight: bold; }
    .gallery { display: flex; flex-wrap: wrap; padding-top: 80px; justify-content: center; }
    .gallery img { margin: 10px; width: 200px; height: auto; cursor: pointer; border-radius: 4px; }
    .modal { display: none; position: fixed; z-index: 2000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); justify-content: center; align-items: center; }
    .modal img { max-width: 90%; max-height: 90%; }
    .close, .prev, .next { position: absolute; top: 50%; transform: translateY(-50%); font-size: 2rem; color: white; background: rgba(0,0,0,0.5); padding: 0.5rem; cursor: pointer; }
    .close { top: 10px; right: 20px; transform: none; font-size: 2rem; }
    .prev { left: 20px; }
    .next { right: 20px; }
  </style>
</head>
<body>
  <nav>
    <a href="index.html">首页</a>
    <a href="gallery.html">摄影作品</a>
    <a href="#">佛经手书</a>
    <a href="#">旅行随笔</a>
    <a href="#">关于我</a>
  </nav>
  <div class="gallery">
"""
    for img in images:
        html += f'    <img src="{IMAGE_FOLDER}/{img}" alt="{img}" onclick="openModal({images.index(img)})">
'

    html += """  </div>
  <div id="myModal" class="modal">
    <span class="close" onclick="closeModal()">&times;</span>
    <span class="prev" onclick="changeImage(-1)">❮</span>
    <img id="modalImage" src="">
    <span class="next" onclick="changeImage(1)">❯</span>
  </div>
  <script>
    const images = %s;
    let currentIndex = 0;

    function openModal(index) {
      currentIndex = index;
      document.getElementById("modalImage").src = "%s/" + images[index];
      document.getElementById("myModal").style.display = "flex";
    }

    function closeModal() {
      document.getElementById("myModal").style.display = "none";
    }

    function changeImage(direction) {
      currentIndex = (currentIndex + direction + images.length) %% images.length;
      document.getElementById("modalImage").src = "%s/" + images[currentIndex];
    }

    document.body.onkeydown = function(e) {
      if (e.key === "Escape") closeModal();
      if (e.key === "ArrowRight") changeImage(1);
      if (e.key === "ArrowLeft") changeImage(-1);
      if (e.key === " ") closeModal();
    };
  </script>
</body>
</html>""" % (images, IMAGE_FOLDER, IMAGE_FOLDER)
    return html

if __name__ == "__main__":
    image_files = get_image_files()
    html_output = generate_html(image_files)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_output)
    print(f"Updated {OUTPUT_FILE} with {len(image_files)} images.")
