# Goalcast 分发指南

## 🚀 快速开始

### 构建所有文件

```bash
# 运行一次完整构建
./scripts/build-all.sh
```

构建完成后，会生成：
- `dist/goalcast-1.0.0-py3-none-any.whl` - Python 主包（数据分析引擎）
- `skills-dist/*.zip` - 每个 Skill 独立的 zip 包

## 📦 构建输出示例

```
dist/
├── goalcast-1.0.0-py3-none-any.whl (80K)    # Python 主包
└── goalcast-1.0.0.tar.gz (225K)             # Python 源码包

skills-dist/
├── goalcast-analyze-1.0.0.zip (4.4K)        # 8 层分析引擎
├── goalcast-get-match-data-1.0.0.zip (2.7K) # 数据获取
├── goalcast-report-1.0.0.zip (2.2K)         # 报告格式化
├── goalcast-schedule-1.0.0.zip (2.2K)       # 赛程获取
├── footystats-1.0.0.zip (3.2K)              # FootyStats 工具
└── SHA256SUMS
```

## 📋 分发文件

### 方案 A：推荐 - 分发 Python wheel + Skills zips

将以下文件发送给其他人：

1. **Python 主包**：`dist/goalcast-1.0.0-py3-none-any.whl`
2. **Skills zips**：`skills-dist/` 目录中的所有 zip 文件
3. **安装文档**：`skills/INSTALL.md`

**优点：**
- ✅ Python 包用 `pip install` 安装
- ✅ Skills 可以单独选择安装
- ✅ 灵活、兼容性好

### 方案 B：分发 Python 源码包 + Skills zips

1. **Python 源码包**：`dist/goalcast-1.0.0.tar.gz`
2. **Skills zips**：`skills-dist/` 目录中的所有 zip 文件

## 📚 接收方安装步骤

### 1. 安装 Python 主包

```bash
pip install dist/goalcast-1.0.0-py3-none-any.whl[ai]
```

### 2. 安装 Skills 到 OpenClaw

**在 OpenClaw 中安装单个 skill：**

```bash
# 安装 8 层分析引擎
openclaw skill install skills-dist/goalcast-analyze-1.0.0.zip

# 安装数据获取 skill
openclaw skill install skills-dist/goalcast-get-match-data-1.0.0.zip

# 安装报告格式化 skill
openclaw skill install skills-dist/goalcast-report-1.0.0.zip
```

**或者批量安装所有 skills：**

```bash
# 解压所有 skills
cd skills-dist
for zip in *.zip; do
    openclaw skill install "$zip"
done
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 API 密钥
# - FOOTYSTATS_API_KEY
# - ODDS_API_KEY
# - ANTHROPIC_API_KEY（可选，用于 AI 分析）
```

### 4. 测试

```bash
# 测试 Python 包
goalcast-match --help

# 测试数据获取
goalcast-match get_match_analysis 8469819

# 在 OpenClaw 中测试 Skills
openclaw
# 然后输入：分析比赛 8469819
```

## 🎯 可选安装

根据需求选择安装 skills：

### 核心 Skills（推荐）

```bash
# 8 层分析引擎 - 核心功能
openclaw skill install skills-dist/goalcast-analyze-1.0.0.zip

# 数据获取 - 必需
openclaw skill install skills-dist/goalcast-get-match-data-1.0.0.zip
```

### 辅助 Skills（可选）

```bash
# 报告格式化 - 美化输出
openclaw skill install skills-dist/goalcast-report-1.0.0.zip

# 赛程获取 - 获取最近比赛
openclaw skill install skills-dist/goalcast-schedule-1.0.0.zip

# FootyStats 工具 - 原始数据调试
openclaw skill install skills-dist/footystats-1.0.0.zip
```

## 📚 详细文档

- [完整安装指南](skills/INSTALL.md)
- [Skills 使用说明](skills/README.md)
- [构建脚本说明](scripts/README.md)
- [快速入门](QUICKSTART.md)

## ❓ 需要帮助？

查看 [skills/INSTALL.md](skills/INSTALL.md) 的故障排查部分。

## 📝 版本说明

- Python 包版本：`1.0.0`
- Skills 版本：与 Python 包版本一致
- 所有同版本的包可以混用
