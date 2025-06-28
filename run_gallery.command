#!/bin/bash
cd "$(dirname "$0")"

# 1. 运行 Python 脚本
echo "⏳ 正在生成 gallery.html..."
python3 generate_gallery.py

# 2. 检查是否成功生成
if [ $? -ne 0 ]; then
  echo "❌ Python 脚本出错，未能生成 gallery.html"
  exit 1
fi

# 3. Git 操作：add、commit、push
echo "📦 添加 images/ 和 gallery.html 到 Git"
git add images/ gallery.html

echo "📝 正在提交更改..."
git commit -m "🖼 自动更新 gallery 和图片" 2>/dev/null

echo "🚀 正在推送到 GitHub..."
git push origin main

echo "✅ 所有操作完成，网站更新成功！"
