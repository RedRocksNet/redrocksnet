
import os

IMAGE_FOLDER = "sutra_images"
OUTPUT_FILE = "sutras.html"

def generate_html(images):
    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>佛经手书</title>
    <style>
        body {{
            font-family: "Noto Serif SC", serif;
            background-color: #fdfcf5;
            margin: 0;
            padding: 0;
            color: #333;
        }}
        header {{
            background-color: #fff;
            padding: 20px;
            text-align: center;
            border-bottom: 1px solid #ccc;
        }}
        h1 {{
            margin: 0;
        }}
        p.description {{
            font-size: 1rem;
            color: #666;
            margin-top: 8px;
        }}
        nav {{
            text-align: center;
            background-color: #f8f8f8;
            padding: 10px 0;
            border-bottom: 1px solid #ccc;
        }}
        nav a {{
            margin: 0 15px;
            text-decoration: none;
            color: #333;
            font-weight: bold;
        }}
        .gallery {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            margin: 20px auto;
            max-width: 1200px;
        }}
        .thumbnail {{
            margin: 8px;
            max-width: 200px;
            max-height: 200px;
            overflow: hidden;
        }}
        .thumbnail img {{
            width: 100%;
            height: auto;
            object-fit: contain;
            cursor: pointer;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            padding-top: 60px;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0,0,0,0.9);
        }}
        .modal-content {{
            margin: auto;
            display: block;
            max-width: 90%;
            max-height: 80vh;
        }}
        .close {{
            position: absolute;
            top: 20px;
            right: 35px;
            color: #fff;
            font-size: 40px;
            font-weight: bold;
            cursor: pointer;
        }}
        .arrow {{
            position: fixed;
            top: 50%;
            transform: translateY(-50%);
            font-size: 3rem;
            color: white;
            cursor: pointer;
            user-select: none;
        }}
        .arrow-left {{
            left: 20px;
        }}
        .arrow-right {{
            right: 20px;
        }}
    </style>
</head>
<body>
    <header>
        <h1>佛经手书</h1>
        <p class="description">居家的日子还是旅途中，每日黎明即起，沐手静书，在一笔一划间感受内心，忘却自我</p>
    </header>
    <nav>
        <a href="index.html">首页</a>
        <a href="gallery.html">摄影作品</a>
        <a href="sutras.html">佛经手书</a>
        <a href="#">旅行随笔</a>
        <a href="#">关于我</a>
    </nav>
    <div class="gallery">
"""
    for i, img in enumerate(images):
        html += f'        <div class="thumbnail"><img src="{IMAGE_FOLDER}/{img}" alt="{img}" onclick="openModal({i})"></div>\n'

    html += """
    </div>
    <div id="myModal" class="modal">
        <span class="close" onclick="closeModal()">&times;</span>
        <img class="modal-content" id="modalImage">
        <span class="arrow arrow-left" onclick="prevImage()">&#10094;</span>
        <span class="arrow arrow-right" onclick="nextImage()">&#10095;</span>
    </div>
    <script>
        let modal = document.getElementById("myModal");
        let modalImg = document.getElementById("modalImage");
        let currentIndex = 0;
        const images = [""" + ",".join(f'"{IMAGE_FOLDER}/{img}"' for img in images) + """];
        function openModal(index) {
            modal.style.display = "block";
            modalImg.src = images[index];
            currentIndex = index;
        }
        function closeModal() {
            modal.style.display = "none";
        }
        function nextImage() {
            currentIndex = (currentIndex + 1) % images.length;
            modalImg.src = images[currentIndex];
        }
        function prevImage() {
            currentIndex = (currentIndex - 1 + images.length) % images.length;
            modalImg.src = images[currentIndex];
        }
        document.addEventListener("keydown", function(event) {
            if (modal.style.display === "block") {
                if (event.key === "ArrowRight") nextImage();
                else if (event.key === "ArrowLeft") prevImage();
                else if (event.key === " ") closeModal();
            }
        });
    </script>
</body>
</html>"""
    return html

if __name__ == "__main__":
    images = sorted([img for img in os.listdir(IMAGE_FOLDER)
                     if img.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))])
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(generate_html(images))
