#!/bin/bash

# Goalcast 快速构建脚本 - 仅构建 wheel
# 使用方法：./scripts/build.sh

set -e

echo "🔨 构建 Goalcast Python 包..."

# 清理
rm -rf dist/ build/ *.egg-info

# 构建
python -m build

echo ""
echo "✅ 构建完成！"
echo ""
echo "📦 生成的文件："
ls -lh dist/
echo ""
echo "💡 安装命令："
echo "   pip install dist/goalcast-*.whl[ai]"
