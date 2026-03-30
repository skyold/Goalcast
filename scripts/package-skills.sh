#!/bin/bash

# Goalcast Skills 打包脚本
# 使用方法：./scripts/package-skills.sh

set -e

echo "📦 打包 Goalcast Skills..."

# 检查 skills 目录
if [ ! -d "skills" ]; then
    echo "❌ 错误：找不到 skills/ 目录"
    exit 1
fi

# 创建输出目录
mkdir -p skills-dist

# 获取版本
SKILLS_VERSION=$(grep "^version" pyproject.toml | head -1 | cut -d'"' -f2)

# 清理旧的
rm -rf skills-dist/*

# 打包
echo "创建 tar.gz..."
tar -czf "skills-dist/goalcast-skills-${SKILLS_VERSION}.tar.gz" skills/

echo "创建 zip..."
cd skills/
zip -r "../skills-dist/goalcast-skills-${SKILLS_VERSION}.zip" ./*
cd ..

echo "生成校验和..."
cd skills-dist
sha256sum goalcast-skills-${SKILLS_VERSION}.tar.gz > SHA256SUMS
sha256sum goalcast-skills-${SKILLS_VERSION}.zip >> SHA256SUMS
cd ..

echo ""
echo "✅ Skills 打包完成！"
echo ""
echo "📦 生成的文件："
ls -lh skills-dist/
echo ""
echo "💡 使用说明："
echo "   tar -xzf skills-dist/goalcast-skills-${SKILLS_VERSION}.tar.gz"
echo "   # 或解压 zip（Windows）"
echo "   unzip skills-dist/goalcast-skills-${SKILLS_VERSION}.zip"
