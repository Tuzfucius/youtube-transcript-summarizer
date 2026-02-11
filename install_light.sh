#!/bin/bash
# Video Summarizer - 轻量化部署
# Mode: light

echo "🎬 Video Summarizer 安装脚本"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "模式: 轻量化部署"
echo "描述: 仅核心功能，适合快速使用"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3"
    exit 1
fi

echo "✅ Python 3 已安装"

# 安装依赖
echo ""
echo "📦 安装依赖..."

pip install youtube-transcript-api 2>/dev/null || echo "  ⚠️ youtube-transcript-api 安装失败"

pip install requests 2>/dev/null || echo "  ⚠️ requests 安装失败"

# 验证安装
echo ""
echo "✅ 安装完成!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "使用方式:"
echo ""
echo "  Python API:"
echo "    from video_summarizer import summarize"
echo "    result = summarize('URL', format='brief')"
echo ""
echo "  CLI:"
echo "    python cli.py url 'URL' -f brief"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
