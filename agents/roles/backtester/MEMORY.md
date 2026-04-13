# Goalcast Backtester — Long-term Memory

## MCP Server 配置
- **服务名称**: goalcast
- **连接地址**: 通过环境变量 `MCP_SERVER_URL` 获取 (或默认本地服务)
- **传输协议**: SSE (mcp-remote)
- **代码仓库**: 通过环境变量 `$WORKSPACE_DIR` 获取 (或取当前执行目录)

## 回测指标定义
- **Brier Score**: 概率预测准确性，越低越好（理想 0）
- **Log Loss**: 信息损失，越低越好（理想 0）
- **ROI**: 投注回报率，越高越好
- **Sharpe Ratio**: 风险调整后收益，>1 为良好
- **Hit Rate**: 方向预测命中率

## 回测报告路径
- `team/data/backtests/backtest_YYYY-MM-DD_to_YYYY-MM-DD.json`

## 分析模型权重（由 GCQ 使用）
- **v2.5**: 权重分布见 `skills/goalcast-analyzer-v25/SKILL.md`
- **v3.0**: 权重分布见 `skills/goalcast-analyzer-v30/SKILL.md`

## 三 Agent 协作
- **GCQ** (Role: Analyst): 分析师 — 产出预测
- **GBT** (Role: Backtester, 我): 回测引擎 — 评估模型
- **GRV** (Role: Reviewer): 复盘引擎 — 赛后对比
- 数据流向: GCQ → predictions/ → GBT 回测 / GRV 复盘 → team/data/diary/ 日志更新

## 任务执行规范
- 具备读取 `team/data/predictions/` 中历史预测数据进行批量回测的能力
- 生成分析报告到 `team/data/backtests/` 并支持生成图表数据
- 根据统计表现对系统策略进行评估，给出超参调优建议
