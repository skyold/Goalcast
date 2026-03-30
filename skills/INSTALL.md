# Goalcast Skills 安装指南

本文档说明如何安装和配置 Goalcast 足球预测系统的 Skills 和 Python 代码。

## 📦 系统组成

Goalcast 系统包含两部分：

1. **Python 包** - 核心数据分析引擎
2. **Claude Code Skills** - AI 助手技能定义

## 🔧 安装步骤

### 步骤 1：安装 Python 包

#### 方式 A：从 PyPI 安装（推荐）

```bash
pip install goalcast[ai]
```

#### 方式 B：从源代码安装（开发模式）

```bash
# 克隆仓库
git clone https://github.com/your-org/Goalcast.git
cd Goalcast

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装包
pip install -e .[ai]
```

#### 方式 C：从 wheel 文件安装

```bash
pip install dist/goalcast-1.0.0-py3-none-any.whl
```

### 步骤 2：配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API 密钥
# - FOOTYSTATS_API_KEY
# - ODDS_API_KEY
# - ANTHROPIC_API_KEY（用于 AI 分析）
```

### 步骤 3：配置 Skills

Skills 位于 `skills/` 目录，支持 Claude Code 和 OpenClaw。

**Claude Code 配置：**

在项目根目录创建 `.claude/settings.json`：
```json
{
  "skills": {
    "goalcast-analyze": {
      "enabled": true,
      "path": "skills/goalcast-analyze"
    },
    "goalcast-get-match-data": {
      "enabled": true,
      "path": "skills/goalcast-get-match-data"
    },
    "goalcast-report": {
      "enabled": true,
      "path": "skills/goalcast-report"
    }
  }
}
```

**OpenClaw 配置：**

在项目根目录创建 `openclaw.json`：
```json
{
  "skills_dir": "skills/",
  "enabled_skills": ["goalcast-analyze", "goalcast-get-match-data", "goalcast-report"]
}
```

或者在命令行指定：
```bash
openclaw --skills-dir skills/
```

## ✅ 验证安装

### 测试 Python 包

```bash
# 测试命令行工具
goalcast-match --help

# 测试数据获取
goalcast-match get_match_analysis <match_id>
```

### 测试 Skills

**在 Claude Code 中：**

1. 打开一个足球比赛分析任务
2. 触发 `goalcast-get-match-data` skill
3. 验证数据是否正确返回

**在 OpenClaw 中：**

1. 启动 OpenClaw：`openclaw --skills-dir skills/`
2. 输入：`分析比赛 8469819`
3. 验证技能是否正确触发

## 🚀 使用方法

### 命令行使用

```bash
# 获取比赛分析数据
goalcast-match get_match_analysis 8469819

# 获取最近比赛
goalcast-schedule --days 7

# 调试模式（显示原始 API 数据）
goalcast-match get_match_analysis 8469819 --debug
```

### 在 AI 助手中使用

**Claude Code:**
```
分析比赛 8469819
```

**OpenClaw:**
```bash
openclaw --skills-dir skills/
# 然后输入：分析比赛 8469819
```

Skills 会自动：
1. 调用 `goalcast-get-match-data` 获取数据
2. 执行 8 层量化分析
3. 生成预测报告

## 📋 依赖要求

- Python 3.10+
- FootyStats API 密钥
- （可选）Anthropic API 密钥（用于 AI 分析）

## 🔍 故障排查

### 问题：找不到 `goalcast-match` 命令

**解决方案：**
```bash
# 确认已安装包
pip show goalcast

# 确认 PATH 包含 pip 安装目录
which goalcast-match
```

### 问题：Skills 未触发

**解决方案：**
1. 检查 `skills/` 目录存在
2. 确认 SKILL.md 文件格式正确
3. 检查 AI 助手配置（Claude Code 或 OpenClaw）是否正确指向 skills 目录
4. 重启 AI 助手

### 问题：API 调用失败

**解决方案：**
1. 检查 `.env` 文件存在且包含正确的 API 密钥
2. 测试 API 连接：
   ```bash
   python -c "from src.provider.footystats.client import FootyStatsProvider; print(FootyStatsProvider().health_check())"
   ```

## 📚 相关文档

- [Skills 使用说明](README.md)
- [8 层分析框架](../../prompts/)
- [API 文档](../../doc/)
- [Claude Code Skills 配置](https://docs.anthropic.com/claude-code/)
- [OpenClaw 配置](https://github.com/openclaw/openclaw)

## 🆘 获取帮助

如有问题，请查看：
- GitHub Issues
- 项目文档
- 联系开发团队
