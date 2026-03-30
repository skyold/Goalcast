# Goalcast 快速入门指南

## 🚀 5 分钟快速开始

### 1. 安装

```bash
# 方式 A：从源代码安装（开发模式）
cd Goalcast
pip install -e .[ai]

# 方式 B：从 wheel 安装（如果已有构建包）
pip install dist/goalcast-1.0.0-py3-none-any.whl[ai]
```

### 2. 配置环境变量

```bash
# 复制模板
cp .env.example .env

# 编辑 .env，填入你的 API 密钥
# 至少需要：
# - FOOTYSTATS_API_KEY
# - ANTHROPIC_API_KEY（用于 AI 分析）
```

### 3. 测试

```bash
# 测试命令行工具
goalcast-match --help

# 测试获取比赛数据（替换为你的 match_id）
goalcast-match get_match_analysis 8469819
```

### 4. 在 Claude Code 中使用

打开 Claude Code，确保 `.trae/skills/` 目录存在：

```
分析比赛 8469819
```

Skills 会自动：
1. 获取比赛数据
2. 执行 8 层量化分析
3. 生成预测报告

## 📋 完整文档

- [安装指南](.trae/skills/INSTALL.md)
- [Skills 使用说明](.trae/skills/README.md)
- [分发流程](.trae/skills/README.md#分发流程)

## 🔧 常用命令

```bash
# 获取最近比赛
goalcast-schedule --days 7

# 获取比赛基础信息
goalcast-match get_match_basic <match_id>

# 获取完整分析数据
goalcast-match get_match_analysis <match_id>

# 调试模式（显示原始 API 数据）
goalcast-match get_match_analysis <match_id> --debug
```

## 📦 打包分发

```bash
# 构建包
python -m build

# 输出：
# dist/goalcast-1.0.0.tar.gz
# dist/goalcast-1.0.0-py3-none-any.whl
```

## ❓ 遇到问题？

查看 [安装指南](.trae/skills/INSTALL.md) 的故障排查部分。
