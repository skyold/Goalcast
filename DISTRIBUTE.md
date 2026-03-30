# Goalcast 分发指南

## 🚀 快速开始

### 构建所有文件

```bash
# 运行一次完整构建
./scripts/build-all.sh
```

构建完成后，会生成：
- `dist/goalcast-1.0.0-py3-none-any.whl` - Python 主包（数据分析引擎）
- `dist/goalcast_skills-1.0.0-py3-none-any.whl` - Skills 包（AI 助手技能）
- `skills-dist/goalcast-skills-1.0.0.tar.gz` - Skills 源码包

## 📦 分发文件

### 方案 A：推荐 - 分发两个 wheel 包

将以下文件发送给其他人：

1. **Python 主包**：`dist/goalcast-1.0.0-py3-none-any.whl`
2. **Skills 包**：`dist/goalcast_skills-1.0.0-py3-none-any.whl`
3. **安装文档**：`skills/INSTALL.md`

**优点：**
- 安装简单，`pip install` 即可
- 自动处理依赖
- 兼容性好

### 方案 B：分发 wheel + Skills 源码包

1. **Python 主包**：`dist/goalcast-1.0.0-py3-none-any.whl`
2. **Skills 源码包**：`skills-dist/goalcast-skills-1.0.0.tar.gz`

## 📋 接收方安装步骤

### 方案 A：安装两个 wheel 包（推荐）

```bash
# 1. 安装 Python 主包
pip install dist/goalcast-1.0.0-py3-none-any.whl[ai]

# 2. 安装 Skills 包
pip install dist/goalcast_skills-1.0.0-py3-none-any.whl

# Skills 会自动安装到 Python site-packages 的 skills/ 目录
```

### 方案 B：安装 wheel + 解压 Skills 源码包

```bash
# 1. 安装 Python 主包
pip install dist/goalcast-1.0.0-py3-none-any.whl[ai]

# 2. 解压 Skills 源码包
tar -xzf goalcast-skills-1.0.0.tar.gz
# skills/ 目录即可使用

# 或者用 pip 安装
pip install skills-dist/goalcast-skills-1.0.0.tar.gz
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 API 密钥
```

### 4. 配置 AI 助手

**Claude Code:**
```json
{
  "skills": {
    "goalcast-analyze": {
      "path": "skills/goalcast-analyze"
    },
    "goalcast-get-match-data": {
      "path": "skills/goalcast-get-match-data"
    },
    "goalcast-report": {
      "path": "skills/goalcast-report"
    }
  }
}
```

**OpenClaw:**
```json
{
  "skills_dir": "skills/"
}
```

**注意：** 如果通过 `pip install goalcast_skills` 安装，skills 目录位于 Python site-packages 中。需要：
- 复制到项目目录，或
- 配置 AI 助手指向 site-packages 中的路径

### 5. 测试

```bash
# 测试 Python 包
goalcast-match --help

# 测试 Skills
# 在 AI 助手中输入：分析比赛 8469819
```

## 📚 详细文档

- [完整安装指南](skills/INSTALL.md)
- [Skills 使用说明](skills/README.md)
- [构建脚本说明](scripts/README.md)
- [快速入门](QUICKSTART.md)

## ❓ 需要帮助？

查看 [skills/INSTALL.md](skills/INSTALL.md) 的故障排查部分。
