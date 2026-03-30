#!/bin/bash

# Goalcast 完整构建脚本
# 使用方法：./scripts/build-all.sh

set -e

echo "======================================"
echo "🏗️  Goalcast 完整构建脚本"
echo "======================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查是否在正确的项目目录
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}错误：请在项目根目录运行此脚本${NC}"
    exit 1
fi

# 检查 skills 目录
if [ ! -d "skills" ]; then
    echo -e "${RED}错误：找不到 skills/ 目录${NC}"
    exit 1
fi

echo -e "${BLUE}📂 项目目录：$(pwd)${NC}"
echo ""

# 清理旧的构建文件
echo -e "${YELLOW}🧹 步骤 1/5: 清理旧的构建文件...${NC}"
rm -rf dist/ build/ *.egg-info
rm -rf skills-dist/ skills/build/ skills/dist/ skills/*.egg-info
echo -e "${GREEN}   ✓ 清理完成${NC}"
echo ""

# 安装构建工具（如果需要）
echo -e "${YELLOW}📦 步骤 2/5: 检查构建工具...${NC}"
if ! command -v python -m build &> /dev/null; then
    echo -e "${YELLOW}   安装构建工具...${NC}"
    pip install build wheel twine --quiet
fi
echo -e "${GREEN}   ✓ 构建工具就绪${NC}"
echo ""

# 构建 Python 包
echo -e "${YELLOW}🔨 步骤 3/5: 构建 Python 包 (goalcast)...${NC}"
python -m build
echo -e "${GREEN}   ✓ Python 包构建完成${NC}"
echo ""

# 构建 Skills 包
echo -e "${YELLOW}🔨 步骤 4/5: 构建 Skills 包 (goalcast-skills)...${NC}"
cd skills
python -m build
cd ..
echo -e "${GREEN}   ✓ Skills 包构建完成${NC}"
echo ""

# 创建 skills 分发包（tar.gz 和 zip）
echo -e "${YELLOW}📦 步骤 5/5: 创建 Skills 分发包...${NC}"

# 创建 skills 分发目录
mkdir -p skills-dist

# 获取版本
SKILLS_VERSION=$(grep "^version" skills/pyproject.toml | head -1 | cut -d'"' -f2)
SKILLS_TAR="skills-dist/goalcast-skills-${SKILLS_VERSION}.tar.gz"
SKILLS_ZIP="skills-dist/goalcast-skills-${SKILLS_VERSION}.zip"

# 从 skills/dist 复制构建好的包
cp skills/dist/goalcast_skills-${SKILLS_VERSION}-py3-none-any.whl dist/
echo -e "${GREEN}   ✓ 复制 Skills wheel 到 dist/ 目录${NC}"

# 创建源码包的分发版本
tar -czf "${SKILLS_TAR}" skills/
echo -e "${GREEN}   ✓ 创建 tar.gz: ${SKILLS_TAR}${NC}"

# 创建 zip 格式（Windows 友好）
cd skills/
zip -r "../${SKILLS_ZIP}" ./*
cd ..
echo -e "${GREEN}   ✓ 创建 zip: ${SKILLS_ZIP}${NC}"

# 生成 checksums
cd skills-dist
sha256sum goalcast-skills-${SKILLS_VERSION}.tar.gz > SHA256SUMS
sha256sum goalcast-skills-${SKILLS_VERSION}.zip >> SHA256SUMS
cd ..
echo -e "${GREEN}   ✓ 生成校验和${NC}"
echo ""

# 显示构建结果
echo "======================================"
echo -e "${GREEN}✅ 构建完成！${NC}"
echo "======================================"
echo ""
echo -e "${BLUE}📦 Python 包 (goalcast):${NC}"
ls -lh dist/*.whl dist/*.tar.gz 2>/dev/null | grep -v skills || true
echo ""
echo -e "${BLUE}📦 Skills 包 (goalcast-skills):${NC}"
ls -lh dist/*skills*.whl 2>/dev/null || echo "   (Skills wheel 已复制到 dist/)"
ls -lh skills-dist/
echo ""
echo "======================================"
echo -e "${YELLOW}📋 分发说明:${NC}"
echo "======================================"
echo ""
echo "1. Python 包安装 (goalcast):"
echo "   pip install dist/goalcast-${SKILLS_VERSION}-py3-none-any.whl[ai]"
echo ""
echo "2. Skills 包安装 (goalcast-skills):"
echo "   pip install dist/goalcast_skills-${SKILLS_VERSION}-py3-none-any.whl"
echo "   # 或从源码包安装"
echo "   pip install skills-dist/goalcast-skills-${SKILLS_VERSION}.tar.gz"
echo ""
echo "3. 或者一起分发："
echo "   - dist/goalcast-${SKILLS_VERSION}-py3-none-any.whl"
echo "   - dist/goalcast_skills-${SKILLS_VERSION}-py3-none-any.whl"
echo ""
echo "======================================"
echo ""
echo -e "${GREEN}🎉 所有文件已准备就绪！${NC}"
