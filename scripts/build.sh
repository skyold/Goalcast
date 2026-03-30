#!/bin/bash

# Goalcast 构建和分发脚本
# 使用方法：./scripts/build.sh

set -e

echo "======================================"
echo "🏗️  Goalcast 构建脚本"
echo "======================================"

# 清理旧的构建文件
echo "🧹 清理旧的构建文件..."
rm -rf dist/ build/ *.egg-info

# 安装构建工具（如果需要）
if ! command -v python -m build &> /dev/null; then
    echo "📦 安装构建工具..."
    pip install build wheel twine
fi

# 构建包
echo "🔨 构建 Python 包..."
python -m build

echo ""
echo "✅ 构建完成！"
echo ""
echo "📦 生成的文件："
ls -lh dist/
echo ""
echo "======================================"
echo "📋 下一步操作："
echo "======================================"
echo ""
echo "1. 本地测试安装："
echo "   pip install dist/goalcast-*.whl[ai]"
echo ""
echo "2. 上传到 PyPI（可选）："
echo "   python -m twine upload dist/*"
echo ""
echo "3. 分发给他人："
echo "   - 发送 dist/goalcast-*.whl 文件"
echo "   - 发送 .trae/skills/ 目录"
echo "   - 提供 INSTALL.md 文档"
echo ""
echo "======================================"
