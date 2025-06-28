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
  <style>
    body {
      background-color: #111;
      color: white;
      font-family: sans-serif;
      margin: 0;
      padding: 0;
    }
    nav {
      background-color: #222;
      padding: 1rem;
      text-align: center;
      position: fixed;
      top: 0;
      width: 100%;
      z-index: 1000;
    }
    nav a {
      color: white;
      margin: 0 1rem;
      text-decoration: none;
      font-weight: bold;
    }
    .gallery {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      padding: 6rem 1rem 2rem;
    }
    .gallery img {
      max-width: 200px;
      margin: 10px;
      cursor: pointer;
      border: 2px solid #444;
      transition: transform 0.3s;
    }
    .gallery img:hover {
      transform: scale(1.05);
    }
    .modal {
      display: none;
      position: fixed;
      z-index: 2000;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0,0,0,0.9);
    }
    .modal img {
      display: block;
      max-width: 90%;
      max-height: 90%;
      margin: auto;
      position: absolute;
      top: 0; left: 0; bottom: 0; right: 0;
    }
    .close {
      position: absolute;
      top: 20px;
      right: 30px;
      font-size: 30px;
      color: white;
      cursor: pointer;
    }
    .nav-btn {
      position: absolute;
      top: 50%;
      transform: translateY(-50%);
      font-size: 40px;
      color: white;
      background: none;
      border: none;
      cursor: pointer;
    }
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
'''

for img in images:
    html += f'  <img src="{IMAGE_FOLDER}/{img}" alt="{img}" onclick="openModal({images.index(img)})">\n'

html += '''</div>

<div class="modal" id="modal">
  <span class="close" onclick="closeModal()">&times;</span>
  <button class="nav-btn prev" onclick="prevImage()">&#10094;</button>
  <img id="modalImage" src="">
  <button class="nav-btn next" onclick="nextImage()">&#10095;</button>
</div>

<script>
  const images = [''' + ', '.join([f'"{IMAGE_FOLDER}/{img}"' for img in images]) + '''];
  let currentIndex = 0;
  const modal = document.getElementById('modal');
  const modalImage = document.getElementById('modalImage');

  function openModal(index) {
    currentIndex = index;
    modalImage.src = images[currentIndex];
    modal.style.display = 'block';
  }

  function closeModal() {
    modal.style.display = 'none';
  }

  function prevImage() {
    currentIndex = (currentIndex - 1 + images.length) % images.length;
    modalImage.src = images[currentIndex];
  }

  function nextImage() {
    currentIndex = (currentIndex + 1) % images.length;
    modalImage.src = images[currentIndex];
  }

  document.body.addEventListener("keydown", function(e) {
    if (modal.style.display !== 'block') return;
    if (e.key === 'ArrowRight') nextImage();
    if (e.key === 'ArrowLeft') prevImage();
    if (e.key === ' ') closeModal();
  });
</script>

</body>
</html>
'''

# 写入 HTML 文件
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ gallery.html 已更新！")