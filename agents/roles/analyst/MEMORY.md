# Goalcast Quant — Long-term Memory

## MCP Server 配置
- **服务名称**: goalcast
- **连接地址**: 通过环境变量 `MCP_SERVER_URL` 获取 (或默认本地服务)
- **传输协议**: SSE (mcp-remote)
- **Provider**: FootyStats, Sportmonks, Understat
- **代码仓库**: 通过环境变量 `$WORKSPACE_DIR` 获取 (或取当前执行目录)

## 分析模型
- **v2.5**: 五层模型 (权重由 `config/settings.py` 或模型定义管理，运行时动态获取)
- **v3.0**: 八层模型 (权重由 `config/settings.py` 或模型定义管理，运行时动态获取)
- **compare**: 并行调度 v2.5 + v3.0，生成对比报告
- **Dashboard**: `scripts/quant_dashboard.py` 每日自动汇总预测、ROI、系统健康度等核心看板。

## 引擎核心逻辑 (Engine Logic)
- **GBT (Backtester)**: 具备 `flatten` 能力以兼容对比报告；评估门槛设定为 `matched_results >= 5`，样本量不足时不给出权重调整建议。
- **GRV (Reviewer)**: 通过外部 Scheduler (如 `scheduler.py` 或 Cron) 触发，扫描 `predictions/` 并抓取结算赛果。

## 报告输出协议 (Standard Reporting Protocol)
- **JSON 第一优先级**: 所有预测、回测、复盘必须产出结构化 JSON，存入 `team/data/` 相应子目录。
- **人类可读报告 (Mandatory)**: 所有 JSON 产出必须伴随一份同名的 Markdown (.md) 报告。
  - **内容要求**: 核心结论前置、数据可视化（表格）、策略建议、风险提示。
  - **存储路径**: 
    - 预测: `team/data/predictions/*.md`
    - 回测: `team/data/backtests/*.md`
    - 复盘: `team/data/results/*.md` 或 `team/data/diary/`
- **沟通规范**: Agent 在回复中必须提供 Markdown 报告的摘要链接，禁止直接倾倒原始数据。

## 三 Agent 协作
- **GCQ** (我): 分析师 — 产出预测 JSON + MD 简报
- **GBT**: 回测引擎 — 评估模型性能 JSON + 性能趋势 MD 报告
- **GRV**: 复盘引擎 — 赛后对比 JSON + 盈亏分析 MD 报告
- 数据流向: GCQ → predictions/ → GRV 复盘 + GBT 回测 → MEMORY.md 迭代
