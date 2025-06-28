import os

def generate_html(images):
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <title>佛经手书</title>
  <style>
    body {{
      background-color: #121212;
      color: white;
      font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
      margin: 0;
      padding: 0;
    }}
    nav {{
      background-color: #1e1e1e;
      padding: 1rem;
      text-align: center;
    }}
    nav a {{
      color: white;
      text-decoration: none;
      margin: 0 1rem;
      font-weight: bold;
    }}
    .description {{
      text-align: center;
      margin-top: 1rem;
      color: #ccc;
    }}
    h1 {{
      display: none;
    }}
    .gallery {{
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      padding: 1rem;
    }}
    .gallery img {{
      width: 200px;
      height: auto;
      margin: 0.5rem;
      object-fit: cover;
      border-radius: 4px;
      cursor: pointer;
      transition: transform 0.3s;
    }}
    .gallery img:hover {{
      transform: scale(1.05);
    }}
    .lightbox {{
      display: none;
      position: fixed;
      z-index: 999;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0,0,0,0.9);
    }}
    .lightbox img {{
      display: block;
      max-width: 90%;
      max-height: 90%;
      margin: 5% auto;
    }}
  </style>
</head>
<body>
 <nav>
    <a href="index.html">首页</a>
    <a href="gallery.html">摄影作品</a>
    <a href="sutras.html">佛经手书</a>
    <a href="about.html">关于我</a> <!-- 添加这一行 -->
  </nav>
  <div class="description">
    居家的日子还是旅途中，每日黎明即起，沐手书佛，在一笔一划间感受内心，忘却自我
  </div>
  <div class="gallery">
    {''.join([f'<img src="sutra_images/{img}" onclick="showLightbox(this.src)">' for img in images])}
  </div>
  <div class="lightbox" id="lightbox" onclick="hideLightbox()">
    <img id="lightbox-img" src="">
  </div>
  <script>
    const images = {images};
    let currentIndex = -1;
    function showLightbox(src) {{
      const lb = document.getElementById('lightbox');
      const lbImg = document.getElementById('lightbox-img');
      lb.style.display = 'block';
      lbImg.src = src;
      currentIndex = images.findIndex(img => src.includes(img));
    }}
    function hideLightbox() {{
      document.getElementById('lightbox').style.display = 'none';
    }}
    document.addEventListener('keydown', function(e) {{
      const lb = document.getElementById('lightbox');
      const lbImg = document.getElementById('lightbox-img');
      if (lb.style.display !== 'block') return;
      if (e.key === 'ArrowRight') {{
        currentIndex = (currentIndex + 1) % images.length;
        lbImg.src = 'sutra_images/' + images[currentIndex];
      }} else if (e.key === 'ArrowLeft') {{
        currentIndex = (currentIndex - 1 + images.length) % images.length;
        lbImg.src = 'sutra_images/' + images[currentIndex];
      }} else if (e.key === ' ') {{
        hideLightbox();
      }}
    }});
  </script>
</body>
</html>"""

if __name__ == "__main__":
    image_dir = "sutra_images"
    images = sorted([f for f in os.listdir(image_dir) if f.lower().endswith(('png','jpg','jpeg','gif'))])
    with open("sutras.html", "w", encoding="utf-8") as f:
        f.write(generate_html(images))
    print("✅ sutras.html 已生成")