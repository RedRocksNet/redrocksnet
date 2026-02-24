import os

IMAGE_FOLDER = "images"
OUTPUT_FILE = "gallery.html"

# 获取所有图片文件
images = [f for f in os.listdir(IMAGE_FOLDER) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
images.sort()

# 生成 HTML 内容
html = '''<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <title>摄影作品集</title>
  <link rel="stylesheet" href="/nav.css">
  <style>
    body {
      background-color: #111;
      color: white;
      font-family: sans-serif;
      margin: 0;
      padding: 0;
    }
    .gallery {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      padding: 6rem 1rem 2rem;
      gap: 1rem;
    }
    .gallery img {
      width: 300px;
      height: auto;
      border-radius: 8px;
      cursor: pointer;
      transition: transform 0.3s;
    }
    .gallery img:hover {
      transform: scale(1.05);
    }
    #lightbox {
      display: none;
      position: fixed;
      z-index: 9999;
      padding-top: 60px;
      left: 0;
      top: 0;
      width: 100%%;
      height: 100%%;
      overflow: auto;
      background-color: rgba(0,0,0,0.9);
    }
    #lightbox img {
      margin: auto;
      display: block;
      width: 80%%;
      max-width: 900px;
    }
    #lightbox .close {
      position: absolute;
      top: 20px;
      right: 35px;
      color: white;
      font-size: 40px;
      font-weight: bold;
      cursor: pointer;
    }
    #lightbox .nav-btn {
      position: absolute;
      top: 50%%;
      font-size: 60px;
      color: white;
      cursor: pointer;
      user-select: none;
      padding: 10px;
    }
    #lightbox .prev {
      left: 20px;
    }
    #lightbox .next {
      right: 20px;
    }
  </style>
</head>
<body>

  <div id="rr-nav-mount" data-current="gallery"></div>

  <div class="gallery">
'''

for img in images:
    html += f'<img src="{IMAGE_FOLDER}/{img}" onclick="openLightbox(\'{IMAGE_FOLDER}/{img}\')" />\n'

html += '''
  </div>

  <div id="lightbox">
    <span class="close" onclick="closeLightbox()">&times;</span>
    <span class="nav-btn prev" onclick="changeImage(-1)">&#10094;</span>
    <img id="lightbox-img" src="">
    <span class="nav-btn next" onclick="changeImage(1)">&#10095;</span>
  </div>

  <script>
    let images = [];
    let currentIndex = 0;

    window.onload = function() {
      images = Array.from(document.querySelectorAll('.gallery img')).map(img => img.src);
    };

    function openLightbox(src) {
      currentIndex = images.indexOf(window.location.origin + '/' + src);
      document.getElementById('lightbox').style.display = "block";
      document.getElementById('lightbox-img').src = src;
    }

    function closeLightbox() {
      document.getElementById('lightbox').style.display = "none";
    }

    function changeImage(direction) {
      currentIndex = (currentIndex + direction + images.length) %% images.length;
      document.getElementById('lightbox-img').src = images[currentIndex];
    }
  </script>

  <script src="/nav.js" defer></script>
</body>
</html>
'''

# 写入文件
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ 已生成 {OUTPUT_FILE}，共 {len(images)} 张图片")