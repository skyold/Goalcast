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
echo -e "${YELLOW}🧹 步骤 1/4: 清理旧的构建文件...${NC}"
rm -rf dist/ build/ *.egg-info
rm -rf skills-dist/
echo -e "${GREEN}   ✓ 清理完成${NC}"
echo ""

# 安装构建工具（如果需要）
echo -e "${YELLOW}📦 步骤 2/4: 检查构建工具...${NC}"
if ! command -v python -m build &> /dev/null; then
    echo -e "${YELLOW}   安装构建工具...${NC}"
    pip install build wheel twine --quiet
fi
echo -e "${GREEN}   ✓ 构建工具就绪${NC}"
echo ""

# 构建 Python 包
echo -e "${YELLOW}🔨 步骤 3/4: 构建 Python 包 (football-datakit)...${NC}"
python -m build
echo -e "${GREEN}   ✓ Python 包构建完成${NC}"
echo ""

# 单独打包每个 skill
echo -e "${YELLOW}📦 步骤 4/4: 单独打包每个 Skill...${NC}"

# 创建 skills 分发目录
mkdir -p skills-dist

# 获取版本
SKILLS_VERSION=$(grep "^version" pyproject.toml | head -1 | cut -d'"' -f2)

# 遍历每个 skill 目录并单独打包
for skill_dir in skills/goalcast-* skills/footystats; do
    if [ -d "$skill_dir" ]; then
        skill_name=$(basename "$skill_dir")
        echo -e "${BLUE}   打包：${skill_name}${NC}"

        # 创建 zip 包
        cd "$skill_dir"
        zip -r "../../skills-dist/${skill_name}-${SKILLS_VERSION}.zip" ./*
        cd ../..

        echo -e "${GREEN}   ✓ ${skill_name}-${SKILLS_VERSION}.zip${NC}"
    fi
done

# 生成 checksums
cd skills-dist
sha256sum *.zip > SHA256SUMS
cd ..

echo -e "${GREEN}   ✓ 生成校验和${NC}"
echo ""

# 显示构建结果
echo "======================================"
echo -e "${GREEN}✅ 构建完成！${NC}"
echo "======================================"
echo ""
echo -e "${BLUE}📦 Python 包 (football-datakit):${NC}"
ls -lh dist/*.whl dist/*.tar.gz 2>/dev/null || true
echo ""
echo -e "${BLUE}📦 独立 Skills 包:${NC}"
ls -lh skills-dist/*.zip
echo ""
echo "======================================"
echo -e "${YELLOW}📋 分发说明:${NC}"
echo "======================================"
echo ""
echo "1. Python 包安装 (football-datakit):"
echo "   pip install dist/football_datakit-${SKILLS_VERSION}-py3-none-any.whl[ai]"
echo ""
echo "2. Skills 安装 (OpenClaw):"
echo "   每个 skill 都是独立的 zip 包，可以单独安装："
ls skills-dist/*.zip | while read zip; do
    name=$(basename "$zip")
    echo "   - ${name}"
done
echo ""
echo "3. 分发文件："
echo "   - dist/football_datakit-${SKILLS_VERSION}-py3-none-any.whl"
echo "   - skills-dist/*.zip (每个 skill 单独一个 zip)"
echo ""
echo "======================================"
echo ""
echo -e "${GREEN}🎉 所有文件已准备就绪！${NC}"
