# Goalcast Reviewer — Long-term Memory

## MCP Server 配置
- **服务名称**: goalcast
- **连接地址**: 通过环境变量 `MCP_SERVER_URL` 获取 (或默认本地服务)
- **传输协议**: SSE (mcp-remote)
- **代码仓库**: 通过环境变量 `$WORKSPACE_DIR` 获取 (或取当前执行目录)

## 数据存储路径
- 预测: `team/data/predictions/YYYY-MM-DD_home_away_method.json`
- 赛果: `team/data/results/YYYY-MM-DD_home_away.json`
- 回测: `team/data/backtests/backtest_YYYY-MM-DD_to_YYYY-MM-DD.json`
- 日记: `team/data/diary/YYYY-MM-DD.md`

## 三 Agent 协作
- **GCQ** (Role: Analyst): 分析师 — 产出预测
- **GBT** (Role: Backtester): 回测引擎 — 评估模型
- **GRV** (Role: Reviewer, 我): 复盘引擎 — 赛后对比
- 数据流向: GCQ → predictions/ → GRV 复盘 → team/data/diary/ 更新 → GBT 批量回测

## 核心约束
- 每场比赛独立复盘记录
- 日记记录 (Diary) 只保留 30 天内详细数据，更早的聚合
- 任务触发: 通过系统外部调度 (如 `scheduler.py` 或 Cron) 触发，执行定期复盘任务
