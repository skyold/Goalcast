# Goalcast Skills 使用说明

## 📁 Skills 结构

```
skills/
├── goalcast-analyze/          # 8 层量化分析引擎
│   ├── SKILL.md              # Skill 定义（英文版）
│   ├── SKILL_zh.md           # Skill 定义（中文版）
│   └── references/
│       └── league-params.md  # 联赛参数配置
├── goalcast-get-match-data/  # 比赛数据获取
│   └── SKILL.md
└── goalcast-report/          # 报告格式化
    └── SKILL.md
```

## 🎯 Skills 功能说明

### 1. goalcast-get-match-data

**功能：** 获取足球比赛的完整分析数据

**触发条件：**
- 用户询问比赛数据
- 用户要求分析比赛
- 用户提供 match_id

**输入：**
```
match_id: "8469819"
```

**输出：** 结构化 JSON，包含：
- 基础信息（比赛时间、比分、状态）
- 统计数据（控球率、射门、角球等）
- 高级数据（xG、进攻、危险进攻）
- 赔率数据（Pinnacle、Soft odds）
- 球队数据（近期状态、历史交锋、赛季统计）

### 2. goalcast-analyze

**功能：** 执行 8 层量化分析

**触发条件：**
- "分析比赛"
- "预测比赛"
- "goalcast analysis"
- "run analysis on match ID"

**分析流程：**
1. **Layer 1 - Base Strength (35%)**: xG 建模、主场优势
2. **Layer 2 - Context Adjustment (20%)**: 伤病、赛程、动力
3. **Layer 3 - Market Analysis (20%)**: Pinnacle 赔率分析
4. **Layer 4 - Tempo and Contradiction (5%)**: 矛盾信号处理
5. **Layer 5 - Dixon-Coles Distribution (10%)**: 比分分布
6. **Layer 6 - Bayesian Update (5%)**: 临场数据更新
7. **Layer 7 - EV and Kelly Decision (5%)**: 价值投注决策
8. **Layer 8 - Confidence Score**: 置信度评分

**输出：** 结构化 JSON 预测报告

### 3. goalcast-report

**功能：** 将分析结果格式化为人类可读的报告

**触发条件：**
- "显示报告"
- "格式化分析结果"
- "display prediction results"

**输出：** Markdown 格式预测报告

## 🚀 分发流程

### 方式 1：完整项目分发（推荐）

**适用场景：** 其他人需要使用完整系统（Claude Code 或 OpenClaw）

**步骤：**

1. **打包 Python 代码**
   ```bash
   # 在项目根目录
   pip install build
   python -m build
   ```

2. **分发包**
   - 发送 `.whl` 文件：`dist/goalcast-1.0.0-py3-none-any.whl`
   - 或发送源码包：`dist/goalcast-1.0.0.tar.gz`

3. **Skills 分发**
   - 源码包已包含 `skills/` 目录
   - 或提供 Git 仓库地址

4. **接收方安装**
   ```bash
   # 安装 Python 包
   pip install goalcast-1.0.0.tar.gz[ai]
   
   # 配置环境变量
   cp .env.example .env
   # 编辑 .env 填入 API 密钥
   
   # Skills 已自动包含在包中，位于项目根目录的 skills/
   ```

### 方式 2：Git 仓库分发

**适用场景：** 团队协作、持续更新

**步骤：**

1. **推送到 Git 仓库**
   ```bash
   git add .
   git commit -m "Goalcast release"
   git push origin main
   ```

2. **接收方安装**
   ```bash
   # 克隆仓库
   git clone https://github.com/your-org/Goalcast.git
   cd Goalcast
   
   # 安装
   pip install -e .[ai]
   
   # Skills 会自动位于 skills/
   ```

### 方式 3：仅 Skills 分发

**适用场景：** 接收方已有 Python 环境

**步骤：**

1. **打包 Skills**
   ```bash
   tar -czf goalcast-skills.tar.gz skills/
   ```

2. **接收方配置**
   - 解压到项目目录（Claude Code 或 OpenClaw）
   - 确保 Python 包已安装
   - 在 AI 助手配置中指向 `skills/` 目录

## 📋 分发清单

分发前请确认：

- [ ] `pyproject.toml` 已创建并配置正确
- [ ] `MANIFEST.in` 包含必要文件
- [ ] `.env.example` 包含所有必要的 API 密钥占位符
- [ ] Skills 中的路径已改为动态（不使用硬编码）
- [ ] 已删除敏感信息（API 密钥、数据库文件等）
- [ ] 已测试安装包可以正常工作
- [ ] 包含安装文档（INSTALL.md）

## 🔐 安全注意事项

**不要分发：**
- `.env` 文件（包含真实 API 密钥）
- `*.db` 数据库文件
- `cache/` 目录
- `logs/` 日志文件
- `.venv/` 虚拟环境
- `data/` 目录（包含本地数据库和缓存）

**检查 `.gitignore` 已排除：**
```
.env
*.db
cache/
logs/
.venv/
data/
```

## ✅ 验证流程

### 1. 本地测试打包

```bash
# 构建包
python -m build

# 在临时环境测试安装
python -m venv /tmp/test-env
source /tmp/test-env/bin/activate
pip install dist/goalcast-1.0.0-py3-none-any.whl[ai]

# 测试命令
goalcast-match --help
goalcast-match get_match_analysis 8469819
```

### 2. 测试 Skills

在 Claude Code 或 OpenClaw 中：
1. 触发 `goalcast-get-match-data`
2. 验证数据返回格式
3. 触发 `goalcast-analyze`
4. 验证分析结果

**Claude Code 配置示例：**
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

**OpenClaw 配置示例：**
```json
{
  "skills_dir": "skills/",
  "enabled_skills": ["goalcast-analyze", "goalcast-get-match-data", "goalcast-report"]
}
```

## 📦 PyPI 发布（可选）

如需公开发布：

```bash
# 安装 twine
pip install twine

# 上传到 PyPI
python -m twine upload dist/*

# 其他人可以安装
pip install goalcast[ai]
```

## 🆘 常见问题

**Q: Skills 不触发怎么办？**
A: 
1. 检查 SKILL.md 的 description 是否包含触发关键词
2. 确认 AI 助手（Claude Code / OpenClaw）已正确配置 skills 目录
3. 重启 AI 助手

**Q: 安装包后找不到命令？**
A: 
1. 确认 pip 安装到了正确的 Python 环境
2. 检查 PATH：`which goalcast-match`
3. 确认 entry points 已正确生成：`pip show goalcast`

**Q: 如何更新已分发的包？**
A: 
1. 修改 `pyproject.toml` 中的 version
2. 重新构建：`python -m build`
3. 分发新版本：`goalcast-1.0.1.tar.gz`

**Q: Claude Code 和 OpenClaw 配置有何不同？**
A: 
- **Claude Code**: 使用 `.claude/settings.json` 或项目级 `.claude/` 配置
- **OpenClaw**: 使用 `openclaw.json` 或命令行参数指定 skills 目录
- 两者都支持相对路径，推荐使用 `skills/` 目录

## 📚 相关资源

- [安装指南](INSTALL.md)
- [8 层分析框架](../../prompts/)
- [Python 打包文档](https://packaging.python.org/)
