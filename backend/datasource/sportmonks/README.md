# Sportmonks 数据源 (极简版)

## 1. 架构概述

Sportmonks 数据源经过极简重构，移除了过去庞杂的多层数据处理架构（如 `collector`、`transformer`、`store` 和 `models` 等）。当前设计旨在以最直接的方式获取 API 数据，并返回适合 Agent 处理的扁平字典（dict）结构。

### 1.1 目录结构

```text
datasource/sportmonks/
├── __init__.py
├── service.py      # 核心服务入口（包含数据获取、处理与简单的文件缓存逻辑）
└── README.md
```

## 2. 核心设计原则

1. **单文件/极简入口**：所有底层的数据访问、组装与缓存逻辑统一在 `service.py` 中实现。
2. **扁平化数据返回**：不再维护复杂的强类型数据模型（如 `Match`, `Team`, `Player` 等对象），直接将 Sportmonks 的原始 JSON 响应解析并裁剪为扁平的 `dict`，这更契合大语言模型（LLM）/ Agent 的理解和处理习惯。
3. **轻量级缓存**：引入内部的 `SimpleCache`，实现基于本地文件的轻量级按需缓存，全面废弃了原有的 SQLite 数据库和深层嵌套的缓存树机制。

## 3. 缓存策略 (SimpleCache)

- **缓存介质**：纯文本 JSON 文件。
- **缓存目录**：保持数据源隔离，存放在 `data/cache/sportmonks/` 目录下。
- **缓存文件命名约定**：
  - 赛程级缓存：`fixtures_{date}.json`
  - 单场比赛级缓存：`match_{id}.json`
- **智能 TTL 策略**：支持根据比赛距离开赛时间的长短智能设置缓存过期时间（TTL）。对于尚未开始的比赛，距离开赛越近刷新越频繁，从而减少不必要的冗余 API 刷新请求。

## 4. 关键数据字段约定与注意事项

- **xG (预期进球) 数据**：
  - 必须在请求 API 时显式使用 `include="xGFixture"`。
  - 数据实际位于响应的 `xgfixture` 或 `xGFixture` 字段下，不再仅是过去的 `expected` 字段。
  - 解析时需匹配目标 `participant_id` 且类型为 `expected` 的数据。
- **赛前数据缺失现象**：
  - 未开赛的比赛通常会缺少赔率 (Odds)、亚盘 (AH) 及其变动数据，首发阵容通常为空或未公布。
  - 检查单场可用性时，应先 `get_match` 再视情况 `refresh_match`。
  - 如果强刷后 xG 出现统一的负值，应视为异常/可疑数据，不予采信。
