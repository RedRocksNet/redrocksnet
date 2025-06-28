import os

def generate_html(images):
    return f"""
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>佛经手书</title>
    <style>
        body {{
            background-color: #121212;
            color: #eee;
            font-family: 'Helvetica Neue', sans-serif;
            margin: 0;
            padding: 0;
        }}
        header {{
            text-align: center;
            padding: 40px 20px 10px;
        }}
        h1 {{
            font-size: 2.5em;
            margin-bottom: 0.2em;
        }}
        p {{
            font-size: 1.1em;
            color: #ccc;
        }}
        nav {{
            display: flex;
            justify-content: center;
            background-color: #1f1f1f;
            padding: 10px 0;
        }}
        nav a {{
            color: #eee;
            margin: 0 15px;
            text-decoration: none;
            font-weight: bold;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            padding: 20px;
            max-width: 1200px;
            margin: auto;
        }}
        .gallery img {{
            width: 100%;
            height: auto;
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.3s;
        }}
        .gallery img:hover {{
            transform: scale(1.03);
        }}
        .lightbox {{
            position: fixed;
            top: 0; left: 0;
            width: 100vw; height: 100vh;
            background-color: rgba(0, 0, 0, 0.9);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }}
        .lightbox img {{
            max-width: 90%;
            max-height: 90%;
        }}
        .arrow {{
            position: fixed;
            top: 50%;
            font-size: 3em;
            color: white;
            cursor: pointer;
            z-index: 1001;
            user-select: none;
        }}
        .arrow.left {{ left: 20px; }}
        .arrow.right {{ right: 20px; }}
    </style>
</head>
<body>
    <header>
        <h1>佛经手书</h1>
        <p>居家的日子还是旅途中，每日黎明即起，沐手书佛，在一笔一划间感受内心，忘却自我</p>
    </header>
    <nav>
        <a href="index.html">首页</a>
        <a href="gallery.html">摄影作品</a>
        <a href="sutras.html">佛经手书</a>
        <a href="#">旅行随笔</a>
        <a href="#">关于我</a>
    </nav>
    <div class="gallery">
        {''.join(f'<img src="sutra_images/{img}" onclick="openLightbox({i})">' for i, img in enumerate(images))}
    </div>
    <div id="lightbox" class="lightbox" style="display:none" onclick="closeLightbox(event)">
        <span class="arrow left" onclick="prevImage(event)">&#8592;</span>
        <img id="lightbox-img">
        <span class="arrow right" onclick="nextImage(event)">&#8594;</span>
    </div>
    <script>
        const images = [{', '.join(f'"sutra_images/{img}"' for img in images)}];
        let currentIndex = 0;

        function openLightbox(index) {{
            event.stopPropagation();
            currentIndex = index;
            document.getElementById('lightbox-img').src = images[index];
            document.getElementById('lightbox').style.display = 'flex';
        }}

        function closeLightbox(event) {{
            if (event.target.id === 'lightbox' || event.code === 'Space') {{
                document.getElementById('lightbox').style.display = 'none';
            }}
        }}

        function nextImage(event) {{
            event.stopPropagation();
            currentIndex = (currentIndex + 1) % images.length;
            document.getElementById('lightbox-img').src = images[currentIndex];
        }}

        function prevImage(event) {{
            event.stopPropagation();
            currentIndex = (currentIndex - 1 + images.length) % images.length;
            document.getElementById('lightbox-img').src = images[currentIndex];
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.code === 'ArrowRight') nextImage(e);
            else if (e.code === 'ArrowLeft') prevImage(e);
            else if (e.code === 'Space') closeLightbox(e);
        }});
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    folder = "sutra_images"
    images = sorted([f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    with open("sutras.html", "w", encoding="utf-8") as f:
        f.write(generate_html(images))
    print("✅ sutras.html 页面生成完毕")
