import os

def get_images(folder="sutra_images"):
    exts = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    return sorted(
        [f for f in os.listdir(folder) if os.path.splitext(f)[1].lower() in exts]
    )

def generate_html(images):
    html = """<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>佛经手书</title>
    <style>
        body {
            background-color: #fdf6e3;
            font-family: sans-serif;
            margin: 0;
            padding: 0;
        }
        h1 {
            text-align: center;
            padding: 20px 10px 10px;
            color: #6b4e2e;
        }
        .intro {
            text-align: center;
            font-size: 1.1em;
            margin-bottom: 10px;
            color: #4e3b2c;
        }
        .gallery {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 10px;
            padding: 10px;
        }
        .gallery img {
            max-width: 100%;
            height: auto;
            width: 200px;
            cursor: pointer;
            border: 1px solid #ccc;
            border-radius: 4px;
            transition: transform 0.2s;
        }
        .gallery img:hover {
            transform: scale(1.03);
        }
        .preview {
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.85);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .preview img {
            max-width: 90%;
            max-height: 90%;
        }
    </style>
</head>
<body>
    <h1>佛经手书</h1>
    <div class="intro">每日黎明即起，手书佛经，在一笔一划中感受内心，忘却自己。</div>
    <div class="gallery">
"""
    for img in images:
        html += f'        <img src="sutra_images/{img}" alt="{img}">\n'

    html += """    </div>
    <div class="preview" id="preview">
        <img id="preview-img" src="">
    </div>
    <script>
        const preview = document.getElementById("preview");
        const previewImg = document.getElementById("preview-img");
        const images = document.querySelectorAll(".gallery img");
        let current = 0;
        images.forEach((img, index) => {
            img.addEventListener("click", () => {
                preview.style.display = "flex";
                previewImg.src = img.src;
                current = index;
            });
        });
        document.addEventListener("keydown", e => {
            if (preview.style.display !== "flex") return;
            if (e.key === " ") preview.style.display = "none";
            else if (e.key === "ArrowRight") {
                current = (current + 1) % images.length;
                previewImg.src = images[current].src;
            } else if (e.key === "ArrowLeft") {
                current = (current - 1 + images.length) % images.length;
                previewImg.src = images[current].src;
            }
        });
        preview.addEventListener("click", () => preview.style.display = "none");
    </script>
</body>
</html>"""
    return html

if __name__ == "__main__":
    print("📜 正在生成 sutras.html 页面...")
    images = get_images()
    with open("sutras.html", "w", encoding="utf-8") as f:
        f.write(generate_html(images))
    print("✅ sutras.html 已生成！")
