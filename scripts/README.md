# Goalcast 构建脚本说明

## 📦 可用脚本

### 1. `build-all.sh` - 完整构建（推荐）

构建 Python wheel 和 Skills 包。

```bash
./scripts/build-all.sh
```

**输出：**
- `dist/goalcast-1.0.0-py3-none-any.whl` - Python wheel
- `dist/goalcast-1.0.0.tar.gz` - Python 源码包
- `skills-dist/goalcast-skills-1.0.0.tar.gz` - Skills tar.gz
- `skills-dist/goalcast-skills-1.0.0.zip` - Skills zip（Windows 友好）
- `skills-dist/SHA256SUMS` - 校验和文件

### 2. `build-wheel.sh` - 仅构建 Python wheel

快速构建 Python 包，不包含 Skills。

```bash
./scripts/build-wheel.sh
```

**输出：**
- `dist/goalcast-1.0.0-py3-none-any.whl`
- `dist/goalcast-1.0.0.tar.gz`

### 3. `package-skills.sh` - 仅打包 Skills

单独打包 Skills，用于快速更新 Skills。

```bash
./scripts/package-skills.sh
```

**输出：**
- `skills-dist/goalcast-skills-1.0.0.tar.gz`
- `skills-dist/goalcast-skills-1.0.0.zip`
- `skills-dist/SHA256SUMS`

## 🚀 使用流程

### 场景 1：完整发布

```bash
# 运行完整构建
./scripts/build-all.sh

# 分发以下文件：
# - dist/goalcast-1.0.0-py3-none-any.whl
# - skills-dist/goalcast-skills-1.0.0.tar.gz
```

### 场景 2：仅更新 Python 代码

```bash
# 快速构建 wheel
./scripts/build-wheel.sh

# 分发 dist/goalcast-1.0.0-py3-none-any.whl
```

### 场景 3：仅更新 Skills

```bash
# 打包 Skills
./scripts/package-skills.sh

# 分发 skills-dist/goalcast-skills-1.0.0.tar.gz
```

## 📋 接收方安装

### Python 包安装

```bash
pip install dist/goalcast-1.0.0-py3-none-any.whl[ai]
```

### Skills 使用

**方式 A：直接使用压缩包**
```bash
tar -xzf goalcast-skills-1.0.0.tar.gz
# skills/ 目录即可使用
```

**方式 B：复制到项目目录**
```bash
# 将 skills/ 复制到项目根目录
cp -r /path/to/goalcast-skills/skills ./
```

## 🔍 验证构建

```bash
# 检查生成的文件
ls -lh dist/
ls -lh skills-dist/

# 验证校验和
cd skills-dist
sha256sum -c SHA256SUMS
```

## 📝 版本管理

版本号在 `pyproject.toml` 中定义：

```toml
[project]
name = "goalcast"
version = "1.0.0"  # 修改这里
```

修改版本后重新运行构建脚本即可。

## 🛠️ 故障排查

**问题：找不到命令**
```bash
# 确保脚本有执行权限
chmod +x scripts/*.sh
```

**问题：构建失败**
```bash
# 确保在虚拟环境中
source .venv/bin/activate

# 重新安装构建工具
pip install build wheel
```

**问题：Skills 目录不存在**
```bash
# 检查当前目录
ls skills/
# 确保在项目根目录运行
```

## 📚 相关文档

- [Skills 安装指南](../skills/INSTALL.md)
- [Skills 使用说明](../skills/README.md)
- [快速入门](../QUICKSTART.md)
