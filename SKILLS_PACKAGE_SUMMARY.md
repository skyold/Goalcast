# Goalcast 独立 Skill 打包方案

## 🎯 方案说明

将**每个 skill 单独打包成 zip**，可以在 OpenClaw 中单独安装每个 skill。

## ✅ 构建输出

运行 `./scripts/build-all.sh` 后生成：

```
dist/
├── goalcast-1.0.0-py3-none-any.whl (80K)   # Python 主包
└── goalcast-1.0.0.tar.gz (225K)            # Python 源码包

skills-dist/
├── goalcast-analyze-1.0.0.zip (4.4K)       # 8 层分析引擎
├── goalcast-get-match-data-1.0.0.zip (2.7K) # 数据获取
├── goalcast-report-1.0.0.zip (2.2K)        # 报告格式化
├── goalcast-schedule-1.0.0.zip (2.2K)      # 赛程获取
├── footystats-1.0.0.zip (3.2K)             # FootyStats 工具
└── SHA256SUMS
```

## 🚀 安装方式

### 1. Python 主包

```bash
pip install dist/goalcast-1.0.0-py3-none-any.whl[ai]
```

### 2. Skills 安装（OpenClaw）

**单个安装：**
```bash
openclaw skill install skills-dist/goalcast-analyze-1.0.0.zip
```

**批量安装：**
```bash
cd skills-dist
for zip in *.zip; do
    openclaw skill install "$zip"
done
```

## 📋 分发文件

每次构建后，分发以下文件：

1. **Python 包**：`dist/goalcast-1.0.0-py3-none-any.whl`
2. **Skills**：`skills-dist/` 目录中的所有 zip 文件
3. **文档**：`DISTRIBUTE.md` 或 `skills/INSTALL.md`

## 🎁 灵活选择

接收方可以根据需求选择安装哪些 skills：

- **核心功能**：`goalcast-analyze` + `goalcast-get-match-data`
- **完整功能**：所有 skills
- **调试工具**：`footystats`（仅开发需要）

## 📝 修改的文件

- ✅ `scripts/build-all.sh` - 每个 skill 单独打包成 zip
- ✅ `DISTRIBUTE.md` - 更新分发说明
- ❌ 删除 `skills/pyproject.toml`（不需要）
- ❌ 删除 `skills/__init__.py`（不需要）

## ✅ 优势

- **灵活**：可以选择安装需要的 skills
- **轻量**：每个 zip 只有 2-5KB
- **易更新**：单个 skill 更新不影响其他
- **兼容**：OpenClaw 原生支持 zip 安装
