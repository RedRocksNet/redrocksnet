import os

SUTRA_FOLDER = "sutra_images"
OUTPUT_HTML = "sutras.html"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>佛经手书图集</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            background: #f4f4f4;
        }}
        h1 {{
            text-align: center;
            padding: 20px;
        }}
        .gallery {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 10px;
            padding: 10px;
        }}
        .gallery img {{
            height: 200px;
            object-fit: contain;
            cursor: pointer;
            transition: transform 0.2s ease;
        }}
        .gallery img:hover {{
            transform: scale(1.05);
        }}
        .preview {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.9);
            display: flex;
            align-items: center;
            justify-content: center;
            display: none;
            z-index: 999;
        }}
        .preview img {{
            max-width: 95vw;
            max-height: 95vh;
        }}
    </style>
</head>
<body>
    <h1>每日佛经手书</h1>
    <div class="gallery">
        {thumbnails}
    </div>
    <div class="preview" id="preview">
        <img id="preview-img" src="">
    </div>
    <script>
        const images = Array.from(document.querySelectorAll('.gallery img'));
        const preview = document.getElementById('preview');
        const previewImg = document.getElementById('preview-img');
        let currentIndex = -1;

        images.forEach((img, index) => {{
            img.addEventListener('click', () => {{
                preview.style.display = 'flex';
                previewImg.src = img.src;
                currentIndex = index;
            }});
        }});

        document.addEventListener('keydown', (e) => {{
            if (preview.style.display === 'flex') {{
                if (e.key === ' ' || e.key === 'Escape') {{
                    preview.style.display = 'none';
                }} else if (e.key === 'ArrowLeft') {{
                    currentIndex = (currentIndex - 1 + images.length) % images.length;
                    previewImg.src = images[currentIndex].src;
                }} else if (e.key === 'ArrowRight') {{
                    currentIndex = (currentIndex + 1) % images.length;
                    previewImg.src = images[currentIndex].src;
                }}
            }}
        }});
    </script>
</body>
</html>
"""

def generate_html():
    if not os.path.isdir(SUTRA_FOLDER):
        print(f"❌ 图片目录不存在：{SUTRA_FOLDER}")
        return
    files = sorted(f for f in os.listdir(SUTRA_FOLDER)
                   if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')))
    if not files:
        print("⚠️ 目录中没有图像文件")
        return
    thumbnails = "\n".join(
        f'<img src="{SUTRA_FOLDER}/{file}" alt="{file}">' for file in files
    )
    html_content = HTML_TEMPLATE.format(thumbnails=thumbnails)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✅ {OUTPUT_HTML} 已生成！")

if __name__ == "__main__":
    generate_html()
