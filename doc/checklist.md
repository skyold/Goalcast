# Goalcast AI — Development Checklist

**版本**: 1.0  
**关联**: spec.md · task.md  
**使用方式**: 每完成一项，将 `[ ]` 改为 `[x]`

---

## Phase 1 · MVP

### 环境搭建

- [ ] 创建项目目录结构（参照 spec.md §6.2）
- [ ] 初始化 Python 虚拟环境（`python -m venv .venv`）
- [ ] 安装基础依赖
  - [ ] `httpx` · `httpx[asyncio]`
  - [ ] `pydantic` v2
  - [ ] `loguru`
  - [ ] `python-dotenv`
  - [ ] `sqlalchemy`
  - [ ] `pandas` · `numpy`
  - [ ] `pytest` · `pytest-asyncio`
- [ ] 创建 `.env.example` 模板，包含所有必要 Key 名称
  - [ ] `FOOTYSTATS_API_KEY`
  - [ ] `ODDS_API_KEY`
  - [ ] `OPENWEATHER_API_KEY`
  - [ ] `ANTHROPIC_API_KEY`
- [ ] 创建 `.gitignore`，排除 `.env` · `*.db` · `__pycache__` · `cache/`
- [ ] 初始化 Git，首次 commit

---

### T1 — 基础设施

- [ ] **settings.py**
  - [ ] 从 `.env` 加载所有 API Key
  - [ ] 定义联赛参数常量表（英超/西甲/意甲/德甲/法甲/欧冠）
  - [ ] 定义主场优势系数
  - [ ] 定义置信度评分加减分规则
  - [ ] 定义 EV 阈值常量（0.05 / 0.10）

- [ ] **logger.py**
  - [ ] 配置 loguru，输出到控制台 + 文件（`logs/goalcast.log`）
  - [ ] 格式：时间戳 + 级别 + 模块 + 消息

- [ ] **rate_limiter.py**
  - [ ] 实现简单令牌桶或 `asyncio.sleep` 封装
  - [ ] 可配置每个数据源的独立速率参数

- [ ] **cache.py**
  - [ ] 实现基于文件的 JSON 缓存（`cache/{source}/{key}.json`）
  - [ ] 支持 TTL：读取时检查时间戳，过期则返回 None
  - [ ] 实现 `cache_get(key)` · `cache_set(key, data, ttl_hours)`

---

### T2 — 数据采集层

#### T2.1 FootyStats

- [ ] 注册账号，获取 API Key，确认套餐（Hobby 起步）
- [ ] **FootyStatsClient 类**
  - [ ] `__init__(api_key, cache)` 初始化
  - [ ] `get_team(team_id) → TeamRawData`
    - [ ] 提取字段：`seasonXG_overall/home/away` · `seasonXGAgainst_*` · `ppg_overall` · `seasonPossession_*` · `seasonAttacks_*`
    - [ ] 缓存 TTL：24 小时
  - [ ] `get_league_matches(season_id, date=None) → list[MatchRaw]`
    - [ ] 提取字段：match_id · homeID · awayID · status · odds_*
    - [ ] 缓存 TTL：1 小时（未开始比赛）· 永久（已结束）
  - [ ] `get_match(match_id) → MatchDetail`
    - [ ] 提取字段：h2h · odds · home/away_league_position · btts_potential
    - [ ] 缓存 TTL：30 分钟（未开始）· 永久（已结束）
  - [ ] `get_league_table(season_id, max_time=None) → LeagueTable`
    - [ ] 提取字段：standings · zone · points · ppg
    - [ ] 缓存 TTL：12 小时
  - [ ] 通用重试逻辑（3 次，指数退避 1s/2s/4s）
  - [ ] 错误处理：429 速率限制 · 500 服务错误 · 网络超时
- [ ] 单元测试（mock HTTP 响应）
  - [ ] 测试正常响应解析
  - [ ] 测试空数据处理
  - [ ] 测试重试逻辑

#### T2.2 ClubElo

- [ ] **ClubEloClient 类**
  - [ ] `get_elo(team_name, date=None) → float`
  - [ ] 读取 CSV 响应，提取最新 Elo 值
  - [ ] 缓存 TTL：48 小时
- [ ] **team_name_map.json**
  - [ ] 英超 20 支球队名称映射
  - [ ] 西甲 20 支球队名称映射
  - [ ] 意甲 20 支球队名称映射
  - [ ] 德甲 18 支球队名称映射
  - [ ] 法甲 18 支球队名称映射
  - [ ] 欧冠常客（约 30 支）
  - [ ] 覆盖率验证：FootyStats 名称 → ClubElo 格式双向可查

#### T2.3 The Odds API

- [ ] 注册账号，获取 API Key（免费套餐）
- [ ] **OddsAPIClient 类**
  - [ ] `get_odds(sport, match_id) → OddsSnapshot`
  - [ ] 提取字段：1X2 赔率（多家博彩）· 时间戳
  - [ ] 实现免费额度用量计数（从响应头读取 `x-requests-remaining`）
  - [ ] 用量不足时警告，切换到手动模式标记
  - [ ] 缓存 TTL：30 分钟
- [ ] 确认支持的足球联赛 sport key 列表（`soccer_epl` · `soccer_spain_la_liga` 等）

#### T2.4 OpenWeatherMap

- [ ] 注册账号，获取免费 API Key
- [ ] **WeatherClient 类**
  - [ ] `get_match_weather(lat, lon, match_dt) → WeatherData`
  - [ ] 提取字段：`wind.speed`（m/s）· `rain.1h`（mm）· `weather[0].main`
  - [ ] 实现天气 → xG 调整量转换
    - [ ] 风速 >8 m/s → 进攻 -0.10 xG
    - [ ] 降水 >5 mm → 进攻 -0.10 xG
    - [ ] 雪/大雾 → 进攻 -0.10 xG
    - [ ] 正常天气 → 0 调整
- [ ] **stadiums.json**
  - [ ] 英超各球场 GPS 坐标（20 座）
  - [ ] 西甲主要球场（20 座）
  - [ ] 意甲主要球场（20 座）
  - [ ] 德甲主要球场（18 座）
  - [ ] 法甲主要球场（18 座）
  - [ ] 欧冠常用球场

---

### T3 — 数据聚合层

#### T3.1 数据模型（schema.py）

- [ ] `MatchInfo`：match_id · home_team · away_team · competition · match_type · kickoff_dt
- [ ] `TeamStats`：xg_home · xg_away · xga_home · xga_away · ppg · possession · recent_form · elo · league_position · zone
- [ ] `OddsData`：opening_1x2 · current_1x2 · implied_prob（计算字段）· movement（计算字段）
- [ ] `ContextData`：injuries · suspensions · schedule_density · motivation · tactical_notes
- [ ] `WeatherData`：wind_speed · rainfall · condition · xg_adjustment
- [ ] `DataQuality`：missing_fields · quality_level（high/medium/low）· confidence_penalty
- [ ] `AnalysisInput`：上述所有模型的聚合，含版本号 + 时间戳
- [ ] **字段验证**
  - [ ] 概率字段范围 [0, 1]
  - [ ] xG 字段范围 [0, 5]
  - [ ] 赔率字段 > 1.0
  - [ ] 必填字段 None 检查

#### T3.2 MatchBuilder

- [ ] `MatchBuilder.__init__(collectors)` 注入所有 Collector
- [ ] `MatchBuilder.build(match_id, manual_overrides={}) → AnalysisInput`
  - [ ] 步骤 1：获取比赛基本信息（FootyStats）
  - [ ] 步骤 2：并发获取双方球队统计（asyncio.gather）
  - [ ] 步骤 3：获取 Elo 评分（ClubElo）
  - [ ] 步骤 4：获取赔率（The Odds API）
  - [ ] 步骤 5：获取积分表位置（FootyStats）
  - [ ] 步骤 6：获取天气（OpenWeatherMap）
  - [ ] 步骤 7：合并 manual_overrides（阵容、伤病）
  - [ ] 步骤 8：零层数据完整性检查
    - [ ] 生成 `missing_fields` 列表
    - [ ] 计算 `quality_level`
    - [ ] 计算 `confidence_penalty`（各缺失项扣分）
- [ ] 错误隔离：单个 Collector 失败不中断整体流程

#### T3.3 手动输入解析器

- [ ] `parse_lineup(text) → list[str]`：支持换行分隔的球员名单
- [ ] `parse_injuries(text) → list[InjuryItem]`：姓名 + 严重程度（缺阵/存疑）
- [ ] `parse_odds(text) → OddsManual`：格式 "主胜@2.10 平局@3.40 客胜@3.20"
- [ ] 容错处理：空输入返回空列表，不抛异常

---

### T4 — 分析引擎层

#### T4.1 提示词管理

- [ ] 创建 `prompts/v3.0.md`，存储完整 v3.0 提示词
- [ ] **PromptBuilder 类**
  - [ ] `build(input: AnalysisInput) → str`
  - [ ] 动态插入：联赛参数表、比赛类型、数据质量注释、数据包内容
  - [ ] 数据质量注释：缺失字段自动转为提示词内的降级说明
  - [ ] 验证生成的 prompt 长度（< 100k tokens）
- [ ] 提示词版本控制：在 prompt 文件头部注明版本

#### T4.2 Claude API Runner

- [ ] 安装 `anthropic` Python SDK
- [ ] **AnalysisRunner 类**
  - [ ] `run(prompt: str) → str`（同步）
  - [ ] 使用 `claude-sonnet-4-6`
  - [ ] `max_tokens=4000`
  - [ ] 实现流式输出（streaming）打印到控制台
  - [ ] 超时设置：120 秒
  - [ ] 重试：最多 2 次，仅对网络错误和 529 重试
  - [ ] 记录 token 用量（用于成本监控）

#### T4.3 输出解析器

- [ ] **OutputParser 类**
  - [ ] `parse(raw: str) → AnalysisOutput`
  - [ ] 提取 JSON：支持 ```json 代码块和纯 JSON 两种格式
  - [ ] 字段校验
    - [ ] 概率三项之和 ∈ [99%, 101%]
    - [ ] 置信度 ∈ [30, 90]
    - [ ] EV 值 ∈ [-1, 2]
    - [ ] `reasoning_chain` 各字段非空
  - [ ] 解析失败时：保存原始响应到 `data/exports/failed/`，记录错误日志，返回 None
  - [ ] 校验失败时：记录警告，仍然返回结果（不阻止使用）

---

### T5 — 存储层

- [ ] **数据库初始化**
  - [ ] 创建 `goalcast.db` SQLite 文件
  - [ ] `analyses` 表：analysis_id · match_id · created_at · prompt_version · input_json · output_json · confidence · ev · bet_rating · actual_result（nullable）· actual_score（nullable）· data_quality
  - [ ] `matches` 表：match_id · home_team · away_team · competition · kickoff_dt · status
  - [ ] `data_quality_log` 表：analysis_id · missing_field · impact
- [ ] **Repository 层**
  - [ ] `save_analysis(analysis_id, input, output)` → bool
  - [ ] `get_analysis(analysis_id)` → dict
  - [ ] `update_result(analysis_id, result, score)` → bool
  - [ ] `list_recent(limit=20)` → list
  - [ ] 连接管理：使用 context manager，确保连接释放

---

### T6 — CLI 入口

- [ ] **analyze_match.py**
  - [ ] 参数解析（`argparse`）
    - [ ] `--match_id` 必填
    - [ ] `--lineup_home` 可选文本
    - [ ] `--lineup_away` 可选文本
    - [ ] `--injuries_home` 可选文本
    - [ ] `--injuries_away` 可选文本
    - [ ] `--odds` 可选文本（手动赔率）
    - [ ] `--dry_run` flag
    - [ ] `--no_cache` flag
  - [ ] 运行流程完整性验证
  - [ ] `--dry_run` 模式：打印 AnalysisInput JSON，不调用 Claude
- [ ] **输出格式化**
  - [ ] 终端彩色输出（成功绿色，警告黄色，错误红色）
  - [ ] 摘要打印：主胜%/平%/客胜% · 最可能比分 · EV · 置信度 · 投注建议
  - [ ] JSON 文件保存：`data/exports/{match_id}_{YYYYMMDD_HHMMSS}.json`

---

### Phase 1 集成测试

- [ ] 端到端测试：给定真实 match_id，完整运行全流程
- [ ] 验证输出 JSON 结构与 spec.md §5.1 一致
- [ ] 验证 `data_quality` 字段在数据缺失时正确降级
- [ ] 验证置信度计算公式正确（对照手算结果）
- [ ] 验证 EV 计算正确
- [ ] 验证存储后可正确读取

---

## Phase 2 · 自动化数据采集

### T7 — Understat

- [ ] 安装 `understatapi`（`pip install understatapi`）
- [ ] **UnderstatClient 封装**
  - [ ] `get_team_stats(team_name, season) → TeamStats`
  - [ ] `get_ppda(team_name, season) → float`
  - [ ] `get_recent_xg(team_name, n=5) → list[float]`
- [ ] 集成到 MatchBuilder（与 FootyStats 数据合并，PPDA 填充 `AnalysisInput.ppda`）
- [ ] 联赛名称映射（FootyStats 格式 → Understat 格式）
- [ ] 批量同步脚本：每周一次更新所有追踪球队的统计数据
- [ ] 单元测试

### T8 — Transfermarkt 伤病

- [ ] 安装 `transfermarkt-scraper` 或自行实现
- [ ] **TransfermarktClient 封装**
  - [ ] `get_injuries(team_id) → list[InjuryItem]`
  - [ ] `get_suspensions(team_id) → list[SuspensionItem]`
  - [ ] 字段：player_name · position · severity · return_date
- [ ] 创建 `config/tm_team_ids.json`（FootyStats team_id → Transfermarkt ID）
- [ ] 伤病分级逻辑：
  - [ ] 自动从 FootyStats 获取球员市场价值
  - [ ] Top 3 市值 + 主力位置 → 核心球员
  - [ ] 其余首发球员 → 重要球员
  - [ ] 非主力 → 边缘球员（忽略）
- [ ] 集成到 MatchBuilder（替换手动输入伤病）

### T9 — 定时调度

- [ ] 安装 `apscheduler`
- [ ] **scheduler.py 配置**
  - [ ] 每天 06:00：`update_standings_and_elo()`
  - [ ] 每天 12:00：`update_team_stats()`
  - [ ] 每周一 02:00：`sync_understat_all()`
  - [ ] 比赛日 -4h：`update_injuries_and_odds(match_ids_today)`
  - [ ] 比赛日 -1h：`snapshot_final_odds(match_ids_today)`
- [ ] 错误处理：任务失败时记录日志，不中断其他任务
- [ ] 健康检查：最后成功执行时间监控

---

## Phase 3 · 高级统计

### T10 — FBref

- [ ] 安装 `soccerdata`（`pip install soccerdata`）
- [ ] 每周批量抓取 PPDA 数据（五大联赛）
- [ ] 写入 SQLite 缓存
- [ ] 实现 FBref → Understat PPDA 降级逻辑
- [ ] 速率限制配置（请求间隔 ≥ 5 秒）

### T11 — 球员模块

- [ ] Understat 球员 NPxG/xA 数据接入
- [ ] 第二层自动计算核心球员缺阵的 xG 调整量
  - [ ] 公式：`xG_adj = player_npxg_per90 × 0.3 × estimated_minutes_share`
- [ ] 停赛风险预测（黄牌累积计算）

---

## Phase 4 · 回测校准

### T12 — 结果归档

- [ ] **update_results.py**
  - [ ] 每天自动查询已结束比赛的实际比分
  - [ ] 匹配历史 `analyses` 记录，填入 `actual_result` · `actual_score`
  - [ ] 计算 `ev_realized`
- [ ] 数据积累达到 50 场后开始分析

### T13 — 校准报告

- [ ] **backtest_report.py**
  - [ ] 按置信度分桶（60-70/70-80/80-90）的实际命中率
  - [ ] Brier Score 计算
  - [ ] 按联赛、按比赛类型分组的准确率
  - [ ] 月度/累计 ROI
  - [ ] 输出 Markdown 报告 + CSV 数据

---

## 质量控制清单（每次 PR 前检查）

### 代码质量
- [ ] 所有新函数有 docstring
- [ ] 无硬编码 API Key
- [ ] 无 `print()` 调试输出（使用 logger）
- [ ] 异常处理不使用裸 `except`（至少 `except Exception as e`）

### 数据安全
- [ ] `.env` 未被提交
- [ ] `cache/` 目录未被提交
- [ ] `goalcast.db` 未被提交

### 测试覆盖
- [ ] 新增的 Collector 有 mock 测试
- [ ] 关键计算函数（EV、置信度、隐含概率）有参数化测试
- [ ] `pytest` 通过率 100%

### Prompt 质量
- [ ] v3.0 提示词版本号与代码中引用一致
- [ ] 提示词更新后，手动运行一次端到端验证输出格式正确

---

## 数据配置文件完成状态

| 配置文件 | 路径 | 状态 |
|----------|------|------|
| 联赛参数表 | `config/settings.py` | `[ ]` |
| 球队名称映射 | `config/team_name_map.json` | `[ ]` |
| 场馆坐标表 | `config/stadiums.json` | `[ ]` |
| Transfermarkt ID 映射 | `config/tm_team_ids.json` | `[ ]` |
| The Odds API 联赛 key | `config/odds_sport_keys.json` | `[ ]` |

---

## API Key 申请状态

| 服务 | 申请链接 | 状态 | 套餐 | 月成本 |
|------|----------|------|------|--------|
| FootyStats | footystats.org/api | `[ ]` | Hobby | £29.99 |
| The Odds API | the-odds-api.com | `[ ]` | Free | $0 |
| OpenWeatherMap | openweathermap.org/api | `[ ]` | Free | $0 |
| Anthropic (Claude) | console.anthropic.com | `[ ]` | Pay-per-use | 按用量 |

---

## 里程碑验收标准

### Milestone 1 — Phase 1 完成
- [ ] 给定任意 FootyStats match_id，30 秒内完成数据采集
- [ ] 手动输入阵容 + 伤病后，60 秒内完成 Claude 分析
- [ ] 输出 JSON 符合 spec.md §5.1 规范
- [ ] 分析结果写入数据库
- [ ] 零层数据检查在任意数据缺失场景下正确触发降级

### Milestone 2 — Phase 2 完成
- [ ] 伤病数据从 Transfermarkt 自动获取（无需手动输入）
- [ ] PPDA 数据从 Understat 自动获取
- [ ] 定时任务稳定运行 7 天无中断

### Milestone 3 — Phase 4 完成
- [ ] 存档分析记录 ≥ 100 场
- [ ] 可生成 Brier Score 和 ROI 报告
- [ ] 置信度 80+ 的比赛实际命中率 > 65%（目标值，供参考）

---

*Goalcast AI Checklist v1.0 — 与 task.md 配套使用*
