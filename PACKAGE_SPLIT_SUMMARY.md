# Goalcast 分开打包方案总结

## 🎯 改进目标

将 Python 包和 Skills 包分开，支持独立安装，提高灵活性和兼容性。

## ✅ 完成的改进

### 1. 独立的 Skills 包配置

**创建的文件：**
- `skills/pyproject.toml` - Skills 包的配置
- `skills/README.md` - Skills 包说明
- `skills/__init__.py` - Python 包初始化文件

**Skills 包配置：**
```toml
[project]
name = "goalcast-skills"
version = "1.0.0"
description = "Goalcast Skills for Claude Code and OpenClaw"
```

### 2. 更新的构建脚本

**`scripts/build-all.sh` 现在执行：**
1. 构建 Python 主包 (`goalcast`)
2. 构建 Skills 包 (`goalcast-skills`)
3. 创建分发包（wheel + tar.gz + zip）
4. 复制 Skills wheel 到 `dist/` 目录

## 📦 构建输出

运行 `./scripts/build-all.sh` 后生成：

```
dist/
├── goalcast-1.0.0-py3-none-any.whl (80K)       # Python 主包
├── goalcast-1.0.0.tar.gz (225K)                # Python 源码包
└── goalcast_skills-1.0.0-py3-none-any.whl (1.9K) # Skills wheel 包

skills-dist/
├── goalcast-skills-1.0.0.tar.gz (21K)          # Skills 源码包
├── goalcast-skills-1.0.0.zip (25K)             # Skills zip
└── SHA256SUMS
```

## 🚀 安装方式

### 方案 A：推荐 - 安装两个 wheel 包

```bash
# 1. Python 主包（数据分析引擎）
pip install dist/goalcast-1.0.0-py3-none-any.whl[ai]

# 2. Skills 包（AI 助手技能）
pip install dist/goalcast_skills-1.0.0-py3-none-any.whl
```

**优点：**
- ✅ 安装简单，一条命令
- ✅ 自动处理依赖
- ✅ 兼容性好（PyPI 标准）
- ✅ 易于更新（`pip install --upgrade`）

### 方案 B：wheel + 源码包

```bash
# 1. Python 主包
pip install dist/goalcast-1.0.0-py3-none-any.whl[ai]

# 2. Skills 源码包
pip install skills-dist/goalcast-skills-1.0.0.tar.gz
```

### 方案 C：仅使用 Python 包，手动配置 Skills

```bash
# 仅安装 Python 主包
pip install dist/goalcast-1.0.0-py3-none-any.whl[ai]

# 手动复制 skills 目录到项目
cp -r /path/to/site-packages/skills ./
```

## 📋 分发方案

### 推荐分发内容

发送以下 3 个文件：
1. `dist/goalcast-1.0.0-py3-none-any.whl` - Python 主包
2. `dist/goalcast_skills-1.0.0-py3-none-any.whl` - Skills 包
3. `DISTRIBUTE.md` - 安装指南

### 可选分发内容

- `skills-dist/goalcast-skills-1.0.0.tar.gz` - Skills 源码包（用于无法使用 wheel 的环境）
- `skills/INSTALL.md` - 详细安装文档

## 🔧 使用场景

### 场景 1：完整安装（新户）

```bash
pip install goalcast[ai]
pip install goalcast-skills
```

### 场景 2：仅更新 Skills

```bash
pip install --upgrade goalcast-skills
```

### 场景 3：仅使用 Python 包（不需要 AI 技能）

```bash
pip install goalcast[ai]
# 不使用 goalcast-skills
```

### 场景 4：开发模式

```bash
# Python 主包
pip install -e .[ai]

# Skills 包
pip install -e skills/
```

## 📊 包的依赖关系

```
goalcast (主包)
├── httpx[asyncio]==0.27.0
├── pydantic==2.9.0
├── loguru==0.7.2
├── python-dotenv==1.0.1
├── sqlalchemy==2.0.35
├── pandas==2.2.3
├── numpy>=1.26.0
└── aiohttp==3.13.3

goalcast-skills (Skills 包)
└── (无 Python 依赖，仅包含 SKILL.md 文件)
```

## 🎁 未来发布到 PyPI

可以分别发布到 PyPI：

```bash
# 发布 Python 主包
python -m twine upload dist/goalcast-1.0.0-*

# 发布 Skills 包
python -m twine upload dist/goalcast_skills-1.0.0-*
```

然后用户可以通过 PyPI 安装：

```bash
pip install goalcast[ai]
pip install goalcast-skills
```

## 📝 修改的文件清单

### 新增文件
- ✅ `skills/pyproject.toml`
- ✅ `skills/README.md`
- ✅ `skills/__init__.py`

### 修改文件
- ✅ `scripts/build-all.sh` - 支持构建两个包
- ✅ `DISTRIBUTE.md` - 更新分发说明
- ✅ `MANIFEST.in` - 排除不必要的目录

## ✅ 验证清单

- [x] Python 主包和 Skills 包独立构建
- [x] Skills wheel 包可以独立安装
- [x] 构建脚本自动复制 Skills wheel 到 `dist/`
- [x] 文档更新完成
- [x] 分发包大小合理（Skills wheel 仅 1.9K）

## 🎉 总结

现在 Goalcast 项目支持：
1. **分开打包** - Python 包和 Skills 包独立
2. **分开安装** - 可以只安装其中一个
3. **灵活分发** - wheel 和源码包两种方式
4. **易于更新** - 每个包可以独立升级

这提高了：
- ✅ 兼容性（不同环境可以选择不同安装方式）
- ✅ 灵活性（用户可以只需要的部分）
- ✅ 可维护性（独立版本管理）
