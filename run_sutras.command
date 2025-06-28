#!/bin/bash
cd "$(dirname "$0")"
echo "📜 正在生成 sutras.html 页面..."
python3 generate_sutras.py

if [ $? -eq 0 ]; then
    echo "✅ sutras.html 已生成！"
else
    echo "❌ sutras.html 生成失败，请检查 Python 脚本"
fi

echo "📄 完成。"
