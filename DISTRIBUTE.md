# Goalcast 分发指南

## 🚀 快速开始

### 构建所有文件

```bash
# 运行一次完整构建
./scripts/build-all.sh
```

构建完成后，会生成：
- `dist/goalcast-1.0.0-py3-none-any.whl` - Python 包
- `skills-dist/goalcast-skills-1.0.0.tar.gz` - Skills 包

## 📦 分发文件

将以下文件发送给其他人：

1. **Python 包**：`dist/goalcast-1.0.0-py3-none-any.whl`
2. **Skills 包**：`skills-dist/goalcast-skills-1.0.0.tar.gz`
3. **安装文档**：`skills/INSTALL.md`

## 📋 接收方安装步骤

### 1. 安装 Python 包

```bash
pip install dist/goalcast-1.0.0-py3-none-any.whl[ai]
```

### 2. 解压 Skills

```bash
tar -xzf goalcast-skills-1.0.0.tar.gz
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
