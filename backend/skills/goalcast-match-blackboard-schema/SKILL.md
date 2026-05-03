---
name: goalcast-match-blackboard-schema
description: Defines the JSON schema and structure for the Goalcast MC-xxx.json blackboard file. Other agents MUST read this skill to understand where to read data and where to write results.
---

# Goalcast Match Blackboard Schema (MC-xxx.json)

本文档定义了 Goalcast 量化系统中单场比赛的数据黑板 (`MC-xxx.json`) 的标准结构。所有的 Agent (Orchestrator, Analyst, Trader, Reviewer, Reporter) 都是基于此单一文件进行数据流转。

由于该文件包含全生命周期的所有原始数据和分析结果，体积可能极大。因此，底层框架会进行「上下文裁剪」，即：当你作为一个 Agent 被唤醒时，你只会收到该 JSON 中与你职责相关的部分节点。

## 顶层字段总览

| 字段 | 类型 | 写入者 | 说明 |
|------|------|--------|------|
| `match_id` | string | Orchestrator | 文件唯一标识，如 `MC-20260428-1234ABCD` |
| `status` | string | 各 Agent 通过 `match_store` 写入 | **主状态机**，驱动轮询调度（见下方生命周期） |
| `orchestrator` | object | Orchestrator (legacy) | 冗余兼容字段，内容与 `metadata` 重复，新代码不应依赖 |
| `metadata` | object | Orchestrator | 比赛基本信息，一次性写入，后续只读 |
| `state` | object | 各 Agent | 各 Agent 子状态（`done`/`pending`），用于人工可读检查 |
| `raw_data` | object | Orchestrator | 原始数据区，体积最大。Analyst 的数据来源 |
| `analysis` | object | Analyst | 分析结果区，按模型版本隔离 |
| `trading` | object | Trader | 交易决策区 |
| `review` | object | Reviewer | 赛前审核区（verdict + checks） |
| `report_ref` | string | Reporter | 最终报告的文件路径引用 |

## status 生命周期（主状态机）

这是驱动所有 Agent 轮询调度的核心字段。每个 Agent 的循环通过 `claim_oldest` 按 status 认领比赛：

```
         Orchestrator 创建
              │
              ▼
          "pending"          ← _analyst_loop 轮询认领
              │
              ▼
          "analyzing"        ← Analyst 处理中（防重复认领）
              │
              ▼
          "analyzed"         ← Analyst 完成 → _trader_loop 轮询认领
              │
              ├──── "feedback" ← Reviewer 打回 → _trader_loop 重新认领（最多3次）
              │
              ▼
          "trading"          ← Trader 处理中
              │
              ▼
          "traded"           ← Trader 完成 → _reviewer_loop 轮询认领
              │
              ▼
          "reviewing"        ← Reviewer 处理中
              │
         ┌────┼────────┐
         ▼    ▼        ▼
    "reviewed" "feedback" "rejected"  ← Reviewer 裁决
         │                   │
         ▼                   ▼
   _reporter_loop        终态（废弃）
         │
         ▼
    "reported"            ← Reporter 完成 → 终态
```

## 数据结构定义 (JSON Schema)

```jsonc
{
  // ── 顶层身份 ───────────────────────────────────────────
  "match_id": "MC-20260428-1234ABCD",

  // ── 主状态机（驱动调度）─────────────────────────────────
  "status": "pending",
  // 可选值: pending | analyzing | analyzed | trading | traded |
  //        reviewing | reviewed | feedback | rejected | reported

  // ── Legacy 兼容（与 metadata 重复，新代码不应依赖）───────
  "orchestrator": {
    "prepared_at": "2026-04-28T10:00:00+08:00",
    "fixture_id": 123456,
    "home_team": "Arsenal",
    "away_team": "Chelsea",
    "league": { /* 完整 league 对象 */ },
    "kickoff_time": "2026-04-28 20:00:00"
  },

  // ── 基本信息（Orchestrator 写入，后续只读）──────────────
  "metadata": {
    "match_id": "MC-20260428-1234ABCD",
    "fixture_id": 123456,
    "home_team": "Arsenal",
    "away_team": "Chelsea",
    "league": {
      "id": 8,
      "name": "Premier League",
      "short_code": "UK PL",
      "country_id": 462
    },
    "kickoff_time": "2026-04-28 20:00:00",
    "requested_models": ["v4.0", "v3.0"],
    "prepared_at": "2026-04-28T10:00:00+08:00"
  },

  // ── 子状态（辅助可读，不参与调度）───────────────────────
  "state": {
    "orchestrator": "done",
    "analyst": "done",
    "trader": "done",
    "reviewer": "done",
    "reporter": "done"
  },
  // 每个子字段值: pending | processing | done

  // ── 原始数据区（Orchestrator 写入，体积最大）────────────
  "raw_data": {
    // Analyst 在分析时必须直接读取此节点，严禁自行调用外部 API
    "sportmonks": {
      "fixture": { /* Sportmonks fixture 完整返回 */ },
      "odds": { /* Sportmonks odds 完整返回 */ }
    }
    // 如果降级到 FootyStats 路由，Orchestrator 会额外填充:
    // "footystats": { ... }
  },

  // ── 分析结果区（Analyst 写入）───────────────────────────
  "analysis": {
    // 按模型版本隔离，每个版本的输出独立
    "v4.0": {
      "home_xg": 1.45,
      "away_xg": 0.89,
      "ah_recommendation": "home -0.5",
      "confidence": 65,
      "home_win_prob": 0.45,
      "draw_prob": 0.30,
      "away_win_prob": 0.25,
      "reasoning_summary": "...",
      "analyzed_at": "2026-04-28T10:01:00+08:00"
    },
    "v3.0": {
      /* 同上结构 */
    }
  },

  // ── 交易决策区（Trader 写入）────────────────────────────
  "trading": {
    "results": {
      "direction": "home",
      "ah_line": "-0.5",
      "best_odds": 1.95,
      "bookmaker": "Pinnacle",
      "stake": 150.00,
      "stake_percentage": "1.5%",
      "ev": 0.05,
      "kelly_fraction": 0.25,
      "status": "EXECUTED",
      "reasoning": "...",
      "traded_at": "2026-04-28T10:02:00+08:00"
    }
  },

  // ── 审核区（Reviewer 写入）──────────────────────────────
  "review": {
    "verdict": "approved",
    // 可选值: approved | feedback | rejected
    // approved → 进入 Reporter 队列
    // feedback → 退回 Trader 重试（最多3次）
    // rejected → 比赛标记为废弃
    "checks": {
      "xg_ah_consistent": true,
      "odds_reasonable": true,
      "kelly_prudent": true
    },
    "notes": "审核通过，xc 与 AH 方向一致，凯利注额在安全范围内",
    "reviewed_at": "2026-04-28T10:03:00+08:00"
  },

  // ── 报告引用（Reporter 写入）────────────────────────────
  "report_ref": "reports/2026-04-28.md"
}
```

## Agent 读写边界约定

### 1. Orchestrator (总管)
- **读**: `sportmonks_leagues.json` (联赛字典), MCP `get_matches` 返回
- **写**: 创建 `MC-xxx.json`，填充 `match_id`, `metadata`, `raw_data`, `state.orchestrator`
- **写**: 通过 `match_store.save()` 写入 legacy `orchestrator` 字段
- **初始状态**: `status: "pending"`

### 2. Analyst (分析师)
- **读**: 仅 `metadata` + `raw_data`（框架通过 `load_partial` 裁剪）
- **写**: `analysis.<model_name>` (按模型版本隔离)
- **状态变更**: `pending` → `analyzing` → `analyzed`
- **严禁**: 读取 `trading`/`review`；自行调用外部 API 获取数据（仅当 `raw_data` 不完整时可调用 `get_match` 补全）

### 3. Trader (交易员)
- **读**: 仅 `metadata` + `analysis`（**严禁读取庞大的 `raw_data`**）
- **写**: `trading.results`
- **状态变更**: `analyzed|feedback` → `trading` → `traded`
- **注意**: 当 Reviewer 打回 (`status=feedback`) 时，Trader 会重新认领并修正

### 4. Reviewer (审核员)
- **读**: `metadata` + `analysis` + `trading`
- **写**: `review` (verdict, checks, notes, reviewed_at)
- **状态变更**: `traded` → `reviewing` → `reviewed|feedback|rejected`
- **重试限制**: feedback 最多触发 3 次 Trader 重试

### 5. Reporter (报告员)
- **读**: `metadata` + `analysis` + `trading` + `review`（仅 `verdict=approved` 的比赛）
- **写**: `report_ref` + 外部 Markdown 文件 (`data/reports/{date}.md`)
- **状态变更**: `reviewed` → `reported`
- **严禁**: 修改 `analysis` 或 `trading` 中的任何数据

## 上下文裁剪机制

底层执行框架 (`agents/core/pipeline.py`) 在唤醒每个 Agent 时，通过 `blackboard.load_partial()` 仅提取所需节点，注入 LLM 上下文。这确保：
- 单文件体积虽大（可能 > 1MB），但每个 Agent 只看到几十 KB 的相关数据
- Analyst 不会看到 Trader 的输出，避免"先入为主"
- Trader 不会加载庞大的 `raw_data`，节省 token 消耗
