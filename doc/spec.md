# Goalcast AI — System Specification

**版本**: 1.0  
**状态**: Draft  
**最后更新**: 2026-03-22  

---

## 1. 项目概述

### 1.1 目标

Goalcast AI 是一套基于量化模型的足球比赛分析系统，核心目标是：

> **在不确定性条件下，系统性识别正期望值（EV）投注机会，实现长期盈利。单场预测准确率是噪声，长期 EV 是信号。**

### 1.2 系统组成

```
Goalcast AI
├── 数据采集层        # 多数据源自动化采集与统一接口
├── 分析引擎层        # v3.0 提示词驱动的 8 层分析框架
├── 输出与存档层      # JSON 结构化输出 + 历史记录数据库
└── 回测校准层        # 预测归档 → 赛后对比 → 模型校准（未来）
```

### 1.3 核心约束

- 不编造统计数字。数据不可得时，必须显式降权而非估算填充
- 置信度上限 90 分，禁止输出"必赢"结论
- 每场分析必须完整执行零层数据检查
- 投注建议仅在 EV > 0.05 时输出

---

## 2. 分析引擎规格（v3.0 Prompt）

### 2.1 八层模型架构

| 层级 | 名称 | 权重 | 核心功能 |
|------|------|------|----------|
| 零层 | 赛前强制检查 | — | 数据可用性 · 降级规则 · 比赛类型分类 |
| 第一层 | 基础实力模型 | 35% | xG/xGA 均值回归 · Elo · 主场优势 |
| 第二层 | 情境调整模型 | 20% | 伤病 · 疲劳 · 动力 · 战术变化 |
| 第三层 | 市场行为分析 | 20% | 开盘/即时赔率 · 精明资金信号 |
| 第四层 | 节奏方差模型 | 5% | PPDA · 控球率 · 开放/封闭型判断 |
| 第五层 | 分布模型 | 10% | Dixon-Coles 修正泊松 · 比分矩阵 |
| 第六层 | 贝叶斯更新 | 5% | 条件触发 · 阵容变化 · 赔率剧变 |
| 第七层 | EV 与 Kelly 决策 | 5% | EV 计算 · 风险调整 · 仓位建议 |
| 第八层 | 置信度校准 | — | 公式化评分 · 数据质量惩罚 |

### 2.2 比赛类型分类

| 类型 | 描述 | 特殊建模逻辑 |
|------|------|--------------|
| A | 联赛常规轮次 | 标准双方动力分析，均值回归正常权重 |
| B | 杯赛单场淘汰 | 防守概率上调，低比分/加时/点球建模，进球方差 +15% |
| C | 双回合次回合 | 输入首回合比分，进球需求建模，战略意图权重提升 |
| D | 关键联赛（积分攸关） | 动力调整系数 ×1.5 |

### 2.3 联赛特征参数

| 联赛 | 主场优势 xG | 场均进球 | 低比分偏差 |
|------|------------|----------|------------|
| 英超 | +0.25 | 2.75 | 中等 |
| 西甲 | +0.22 | 2.65 | 较高 |
| 意甲 | +0.20 | 2.55 | 高 |
| 德甲 | +0.28 | 3.05 | 低 |
| 法甲 | +0.26 | 2.60 | 中等 |
| 欧冠 | +0.18 | 2.50 | 高 |

### 2.4 数据缺失降级规则

| 缺失数据 | 降级处理 |
|----------|----------|
| FotMob 阵容不可用 | 第二层调整幅度上限压缩至 ±0.2 xG，置信度 -10 |
| 仅有开盘赔率，无即时赔率 | 第三层权重自动降至 5%，标注"低可信度" |
| ESPN/FootyStats 数据不可用 | 第一层声明"基于估算"，data_quality 标注 low |
| 禁止 | 编造任何统计数字 |

### 2.5 置信度评分公式

```
基础分 = 70

加分：
  + 10  市场方向与模型一致
  +  5  阵容已由 FotMob 确认
  +  5  双方近期状态稳定

扣分：
  - 10  FotMob 阵容不可用
  - 10  统计数据严重缺失
  -  5  赔率方向与模型相反
  -  5  高方差比赛（开放型 + 杯赛）
  - 10  C 类比赛（结果不确定性天然高）
  -  5  赛前重大不确定事件

范围：[30, 90]，禁止超过 90
```

### 2.6 EV 与 Kelly 决策规则

```
EV = (模型概率 × 赔率) - 1

风险调整：
  阵容不确定     × 0.85
  高方差比赛     × 0.90
  市场强烈背离   × 0.85
  （叠加时取乘积）

投注决策：
  EV_adj > 0.10 + 信心 > 70  →  推荐，标准仓位
  EV_adj 0.05~0.10 + 信心高  →  小注
  EV_adj < 0.05              →  不推荐，无论信心高低
```

---

## 3. 数据架构

### 3.1 数据分类

**基础数据**：直接从外部数据源采集，不经计算。  
**派生数据**：由基础数据通过公式或模型计算所得，在分析引擎内部生成。

### 3.2 所有数据字段

#### A. 赛事基础信息

| 字段 | 类型 | 来源 | 层级 |
|------|------|------|------|
| 主客队名称 | 基础 | 手动输入 | 零层 |
| 所属联赛 | 基础 | 手动输入 | 第一层 |
| 比赛类型 A/B/C/D | 派生 | 人工判断 | 零层 |
| 首回合比分（C类） | 基础 | FootyStats / 官方 | 零层 + 第二层 |

#### B. 球队赛季统计

| 字段 | 类型 | 来源 | 层级 |
|------|------|------|------|
| 场均进攻 xG（主/客场） | 基础 | FootyStats · Understat | 第一层 |
| 场均防守 xGA（主/客场） | 基础 | FootyStats · Understat | 第一层 |
| 场均实际进球/失球 | 基础 | FootyStats | 第一层 |
| 近期5场胜平负 | 基础 | FootyStats | 第一层 |
| PPG / 积分 | 基础 | FootyStats | 第二层 |

#### C. 节奏数据

| 字段 | 类型 | 来源 | 层级 |
|------|------|------|------|
| 场均控球率 % | 基础 | FootyStats | 第四层 |
| PPDA（逼抢强度） | 基础 | Understat · FBref | 第四层 |
| 危险进攻次数 | 基础 | FootyStats | 第四层 |

#### D. Elo 评分

| 字段 | 类型 | 来源 | 层级 |
|------|------|------|------|
| 当前 Elo（双方） | 基础 | ClubElo API | 第一层 |
| Elo 胜率概率 | 派生 | 计算：1/(1+10^(ΔElo/400)) | 第一层 |

#### E. 即时情境

| 字段 | 类型 | 来源 | 层级 |
|------|------|------|------|
| 伤病/停赛名单 | 基础 | Transfermarkt · 手动 | 第二层 |
| 7天内赛程密度 | 基础 | FootyStats 赛历 | 第二层 |
| 积分榜排名/与目标差 | 基础 | FootyStats 积分表 | 第二层 |
| 主教练赛前表态 | 基础 | 新闻 / Claude 搜索 | 第二层 |
| 天气数据 | 基础 | OpenWeatherMap API | 第二层 |

#### F. 市场赔率

| 字段 | 类型 | 来源 | 层级 |
|------|------|------|------|
| 开盘赔率 1X2 | 基础 | FootyStats · The Odds API | 第三层 |
| 即时赔率 1X2 | 基础 | The Odds API · OddsPortal 手动 | 第三层 |
| 市场隐含概率 | 派生 | 去 vig 计算 | 第三层 |
| 赔率变动幅度 % | 派生 | 即时-开盘差值 | 第三层 |

#### G. 阵容

| 字段 | 类型 | 来源 | 层级 |
|------|------|------|------|
| 官方首发阵容（11人） | 基础 | FotMob（手动） | 零层 + 第六层 |
| 预期阵容 | 基础 | BBC Sport / 手动 | 第二层 |

#### H. 核心派生数据（引擎内计算）

| 字段 | 计算公式 |
|------|----------|
| 均值回归 xG | `赛季xG × 0.7 + 近5场xG × 0.3` |
| 主场调整 xG | `均值回归xG + 联赛主场优势系数` |
| 情境调整 xG | `主场调整xG + Σ(伤病+疲劳+动力+战术)调整` |
| DC 泊松比分矩阵 | Dixon-Coles 修正，ρ 校正低比分区间 |
| 胜平负概率 | 矩阵行列加总 |
| 市场分歧 | `模型概率 - 市场隐含概率` |
| EV | `(模型概率 × 赔率) - 1` |
| 风险调整 EV | `EV × Π(风险系数)` |
| 置信度评分 | 见 2.5 节公式 |

---

## 4. 数据源规格

### 4.1 FootyStats API（核心主力）

- **用途**：球队 xG/xGA、历史比赛、积分表、开盘赔率、H2H
- **接入**：REST API，`?key=API_KEY`，JSON 响应
- **套餐**：Hobby £29.99/月（Serious £69.99/月）
- **速率**：1800 次/小时（Hobby）
- **主要端点**：
  - `GET /team?team_id=*` — 球队赛季统计
  - `GET /league-matches?season_id=*&date=*` — 比赛列表
  - `GET /match?match_id=*` — 比赛详情 + H2H
  - `GET /league-tables?season_id=*` — 积分表（支持 `max_time` 历史快照）
- **局限**：无首发阵容，无即时赔率变动，无 PPDA

### 4.2 Understat（免费，强力补充）

- **用途**：xG/xGA 每场明细、PPDA、球员 NPxG/xA
- **接入**：页面内嵌 JSON，使用 `understatapi` PyPI 包
- **覆盖**：英超、西甲、意甲、德甲、法甲、俄超（2014 至今）
- **速率**：建议间隔 1-2 秒
- **局限**：无官方 API，页面结构变动风险

### 4.3 ClubElo API（免费，即插即用）

- **用途**：球队 Elo 评分（历史序列 + 当前值）
- **接入**：`GET http://api.clubelo.com/{TeamName}` → CSV
- **注意**：球队名称需连字符格式（`Manchester-City`），维护映射表
- **局限**：更新有 1-2 天延迟

### 4.4 The Odds API（赔率自动化）

- **用途**：实时 1X2 赔率、大小球赔率
- **接入**：REST API，`?apiKey=KEY`，JSON
- **套餐**：免费 500 次/月，付费 $15+/月
- **主端点**：`GET /v4/sports/soccer_epl/odds?regions=eu&markets=h2h`
- **推荐**：Phase 1 用免费额度，需要自动化时升级

### 4.5 Transfermarkt（伤病数据）

- **用途**：伤病名单、停赛名单、球员市场价值
- **接入**：HTML 抓取，使用 `transfermarkt-scraper` PyPI 包
- **更新频率**：官方通报后 6-12 小时更新
- **注意**：德语 URL 结构，需维护球队 ID 映射

### 4.6 FBref（高级战术统计，Phase 3）

- **用途**：PPDA（备用）、Progressive passes、Pressure 数据
- **接入**：`pandas.read_html()` 或 `soccerdata` 库
- **速率**：严格，请求间隔 ≥5 秒，建议每周批量更新一次
- **缓存策略**：写入本地 SQLite，分析时从库读取

### 4.7 OpenWeatherMap（可选天气）

- **用途**：比赛城市赛前天气（风速、降水）
- **接入**：`GET /data/2.5/forecast?lat=*&lon=*&appid=KEY`
- **套餐**：免费额度 60 次/分钟，完全足够
- **触发条件**：风速 >8m/s 或降水 >5mm 才产生 xG 调整

### 4.8 FotMob（阵容，手动为主）

- **用途**：官方首发阵容（开球前 1 小时）
- **接入方式**：手动查看 App，复制粘贴到系统
- **自动化风险**：逆向 API 违反 ToS，随时失效，不建议开发
- **替代**：LiveScore.com 作为备用手动来源

---

## 5. 系统输出规格

### 5.1 标准 JSON 输出结构

```json
{
  "match_info": {
    "home_team": "",
    "away_team": "",
    "competition": "",
    "match_type": "A|B|C|D",
    "data_quality": "high|medium|low",
    "missing_data": []
  },
  "model_output": {
    "base_xg": { "home": 0.0, "away": 0.0 },
    "adjusted_xg": { "home": 0.0, "away": 0.0 },
    "final_probabilities": {
      "home_win": "0%",
      "draw": "0%",
      "away_win": "0%"
    },
    "top_scores": [
      { "score": "1-0", "probability": "0%" },
      { "score": "1-1", "probability": "0%" },
      { "score": "2-1", "probability": "0%" }
    ]
  },
  "market": {
    "market_probabilities": { "home_win": "0%", "draw": "0%", "away_win": "0%" },
    "divergence": { "home_win": 0.0, "draw": 0.0, "away_win": 0.0 },
    "signal_direction": "支持模型|反对模型|中立",
    "signal_strength": "强|中|弱"
  },
  "decision": {
    "ev": 0.0,
    "risk_adjusted_ev": 0.0,
    "best_bet": "",
    "bet_rating": "推荐|小注|不推荐",
    "confidence": 0
  },
  "reasoning_chain": {
    "layer1_summary": "",
    "layer2_adjustments": [],
    "layer3_signal": "",
    "layer4_tempo": "",
    "layer5_top_score_logic": "",
    "layer6_bayesian_update": "跳过|[更新内容]",
    "layer7_ev_calc": "",
    "layer8_confidence_breakdown": ""
  },
  "meta": {
    "match_type_classification": "",
    "league_params_used": "",
    "data_quality_notes": ""
  }
}
```

### 5.2 历史存档格式（未来回测用）

每场分析完成后，将 JSON 输出 + 以下字段写入数据库：

```
analysis_id      UUID
match_id         FootyStats match ID
analyzed_at      ISO 8601 timestamp
actual_result    赛后填入（home_win | draw | away_win）
actual_score     赛后填入
ev_realized      赛后计算：实际赔率收益
confidence_bin   10分段（60-70, 70-80, 80-90）
```

---

## 6. 技术栈

### 6.1 推荐技术选型

| 组件 | 技术 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | 数据生态最完整 |
| HTTP 客户端 | `httpx`（异步）| 比 requests 更现代，支持异步 |
| HTML 抓取 | `playwright` | JS 渲染页面必备 |
| 数据处理 | `pandas` + `numpy` | 标准 |
| 本地数据库 | `SQLite` + `SQLAlchemy` | 轻量，无需服务器 |
| 任务调度 | `APScheduler` | 定时数据更新 |
| 配置管理 | `python-dotenv` | API Key 管理 |
| 日志 | `loguru` | 比标准库 logging 更易用 |
| 测试 | `pytest` | 标准 |

### 6.2 项目目录结构

```
goalcast/
├── config/
│   ├── .env                    # API Keys（不提交 Git）
│   ├── .env.example            # 模板
│   └── settings.py             # 全局配置
│
├── data/
│   ├── db/
│   │   └── goalcast.db         # SQLite 数据库
│   ├── cache/                  # 爬取缓存
│   └── exports/                # JSON 分析输出
│
├── src/
│   ├── collectors/             # 数据采集层
│   │   ├── __init__.py
│   │   ├── footystats.py       # FootyStats API 客户端
│   │   ├── understat.py        # Understat 抓取
│   │   ├── clubelo.py          # ClubElo API 客户端
│   │   ├── odds_api.py         # The Odds API 客户端
│   │   ├── transfermarkt.py    # 伤病数据抓取
│   │   └── weather.py          # OpenWeatherMap 客户端
│   │
│   ├── aggregator/             # 数据聚合层
│   │   ├── __init__.py
│   │   ├── match_builder.py    # 组装单场分析输入包
│   │   └── schema.py           # Pydantic 数据模型
│   │
│   ├── engine/                 # 分析引擎层
│   │   ├── __init__.py
│   │   ├── prompt.py           # v3.0 提示词管理
│   │   ├── runner.py           # Claude API 调用
│   │   └── parser.py           # JSON 输出解析与校验
│   │
│   ├── storage/                # 存储层
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy ORM 模型
│   │   └── repository.py       # 数据库操作
│   │
│   └── utils/
│       ├── rate_limiter.py     # 请求频率控制
│       ├── cache.py            # 本地缓存管理
│       └── logger.py           # 日志配置
│
├── scripts/
│   ├── analyze_match.py        # 单场分析入口（CLI）
│   ├── update_data.py          # 定时数据更新
│   └── backtest.py             # 回测脚本（未来）
│
├── tests/
│   ├── test_collectors/
│   ├── test_aggregator/
│   └── test_engine/
│
├── requirements.txt
├── README.md
├── spec.md                     # 本文档
├── task.md
└── checklist.md
```

---

## 7. 核心业务规则

### 7.1 分析触发条件

- 手动触发：用户运行 `python scripts/analyze_match.py --match_id=*`
- 数据包完整性：零层检查通过后才进入分析引擎
- 阵容确认：FotMob 首发官宣后（开球前 ~60 分钟）为最佳触发时机

### 7.2 数据新鲜度要求

| 数据类型 | 最长可用时间 | 超期处理 |
|----------|--------------|----------|
| 赛季统计（xG/xGA） | 7 天 | 警告，不阻止 |
| 近期形势（近5场） | 3 天 | 警告 |
| 伤病名单 | 48 小时 | 置信度 -5，标注 |
| 赔率数据 | 2 小时 | 标注为旧数据 |
| 首发阵容 | 赛前官宣后 | 未官宣则使用预测版 |

### 7.3 禁止行为（Prompt 层面）

1. 禁止编造统计数字
2. 禁止情感化语言（"状态火热"/"势如破竹"）
3. 禁止 xG 特征重复计算（各层明确分工）
4. 禁止置信度超过 90 分
5. 禁止在低 EV 情况下推荐投注
6. 禁止跳过零层数据检查
7. 禁止用叙述性新闻代替结构化调整量

---

## 8. 非功能性需求

### 8.1 性能

- 单场数据采集完成时间：< 30 秒
- Claude API 分析响应时间：< 60 秒（含重试）
- 本地数据库查询响应：< 1 秒

### 8.2 可靠性

- 所有外部 API 调用必须有重试机制（最多 3 次，指数退避）
- 数据采集失败时，零层降级规则自动生效，不中断分析
- JSON 输出解析失败时，保留原始响应并记录错误

### 8.3 可维护性

- 每个数据源封装为独立 Client 类，接口统一
- API Key 全部通过环境变量管理，不硬编码
- 数据源变更（URL 结构改变）只需修改对应 Collector，不影响其他层

---

## 9. 已知局限与未来扩展

### 9.1 当前版本局限

| 局限 | 影响 | 缓解措施 |
|------|------|----------|
| 无历史回测记录 | 置信度公式和权重为经验值，未数据校准 | 从第一场开始存档，逐步积累 |
| FotMob 阵容手动 | 赛前需人工介入 | 接受此限制，考虑 API-Football 付费替代 |
| 即时赔率非实时 | 第三层信号强度打折 | The Odds API 免费额度可覆盖手动触发场景 |
| 联赛参数静态 | 每赛季需人工更新参数 | 加入赛季开始提醒，每年更新一次 |
| 无球员级 NPxG | 第二层球员影响评估粗糙 | Phase 3 引入 Understat 球员数据模块 |

### 9.2 未来版本规划

**Phase 2（自动化）**
- Understat + Transfermarkt 定时自动抓取
- 本地 SQLite 数据库缓存，分析时从库读取

**Phase 3（高级统计）**
- FBref 高级战术统计（PPDA 精化）
- 球员级 NPxG/xA 分析模块
- OpenWeatherMap 天气自动化

**Phase 4（回测与校准）**
- 历史预测存档 → 赛后结果对比
- 置信度评分校准（Brier Score 评估）
- 各层权重数据驱动优化

**Phase 5（专业级）**
- Betfair Exchange 成交量 / 精明资金信号
- 亚盘市场分析模块
- 多联赛并行分析仪表盘

---

*Goalcast AI Spec v1.0 — 基于 v3.0 提示词分析框架*
