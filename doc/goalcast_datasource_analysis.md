# Goalcast — 数据源全景分析

# 数据源全景分析
// 9 个数据源 · 获取方法 · 字段详情 · 工具开发可行性

**所有数据源一览**

| 数据源 | 获取方式 | 成本 | 核心价值 | 开发难度 | 综合评级 |
| --- | --- | --- | --- | --- | --- |
| FootyStats | 官方 API | £30–70/月 | 球队xG、历史比赛、赔率 | 低 | 核心主力 |
| Understat | JSON抓取 | 免费 | xG/xA、PPDA、球员级数据 | 低 | 强力补充 |
| ClubElo | 官方 API | 免费 | Elo 评分历史序列 | 极低 | 即插即用 |
| FBref | HTML抓取 | 免费 | PPDA、高级战术统计 | 中 | 按需使用 |
| OddsPortal | 结构化抓取 | 免费 | 历史赔率 + 变动追踪 | 中高 | 重要但难 |
| The Odds API | 官方 API | $15+/月 | 即时赔率自动化 | 低 | 升级时引入 |
| Transfermarkt | HTML抓取 | 免费 | 伤病 / 停赛名单 | 中 | 按需使用 |
| FotMob | 逆向API（风险） | 免费 | 官方首发阵容 | 高（法律风险） | 手动为主 |
| OpenWeatherMap | 官方 API | 免费额度 | 比赛当地天气 | 极低 | 可选附加 |
| BBC Sport | HTML抓取 | 免费 | 伤病确认、赛前新闻 | 高（结构不稳定） | 手动更可靠 |
| Betfair Exchange | 官方 API | 免费（需账户） | 实时成交量、精明资金 | 高（需账户认证） | 未来高级版本 |

### FootyStats API

**URL**: footystats.org/api/documentations

最核心的付费数据源。覆盖赛季级球队统计、历史比赛、联赛积分表和开盘赔率，是整套系统的统计骨架。

🟢 官方 REST API 🔵 JSON 响应 🟡 £29–390/月 ⚪ 750+ 联赛

**核心数据字段**

- **球队 xG / xGA** `(seasonXG_overall/home/away · seasonXGAgainst_*)` — 主客场分开，v3.0第一层直接输入
- **BTTS / Over-Under 频率** `(seasonBTTS_* · seasonScoredOver05~35*)` — 细分到主客场、1H/2H，极为完整
- **场均控球率** `(seasonPossession_overall/home/away)` — 第四层节奏判断基础
- **PPG / 胜平负分布** `(ppg_overall · seasonWins/Draws/Losses_*)` — 第二层动力分析依据
- **开盘赔率 1X2** `(odds_ft_home_team_win · odds_ft_draw · odds_ft_away_team_win)` — 第三层开盘隐含概率基线
- **历史 H2H 交锋** `(match endpoint → h2h 数组)` — 含完整比赛统计
- **联赛积分表（含历史快照）** `(league-tables?max_time=UNIX_TS)` — 回测时可查任意时间点的积分榜
- **联赛分区（欧战/降级）** `(zone: { name, number })` — 判断球队处于保级或争冠区
- **射门 / 危险进攻数** `(seasonAttacks_* · seasonDangerousAttacks_*)` — 节奏判断辅助字段
- **角球统计** `(seasonCornersFor/Against_* · corners_over_*)` — 未来大小角球投注模块

#### // 接入方式
- **认证**: URL参数`?key=YOUR_API_KEY`，申请后即得
- **主要端点**: `/team?team_id=*`球队赛季统计`/league-matches?season_id=*&date=*`比赛列表`/match?match_id=*`比赛详情+H2H`/league-tables?season_id=*`积分表
- **速率限制**: Hobby: 1800次/小时 · Serious: 3600次/小时
- **数据格式**: 标准 JSON，结构稳定，文档完整
- **Python库**: 无官方SDK，直接用`requests`+`pandas`即可，约50行完成核心封装

#### // 开发可行性评估
- **接入难度**: 9/10 (90%)
- **数据质量**: 8.5/10 (85%)
- **稳定性**: 9/10 (90%)
- **成本效益**: 8/10 (80%)

  - 官方 API，ToS 明确允许个人和商业使用，法律风险为零
  - 关键局限：无首发阵容、无即时赔率变动、无 PPDA；这三项必须由其他来源补充
  - Hobby 套餐（£29.99/月）对于分析五大联赛已完全足够
  - 建议封装为FootyStatsClient类，统一缓存+速率控制，开发周期约 2 天

---

### Understat

**URL**: understat.com

免费的高质量 xG 数据库，覆盖六大联赛（英超、西甲、意甲、德甲、法甲、俄超）。页面内嵌 JSON 数据，可直接提取，无需复杂爬取。

🟢 无官方API，页面内嵌JSON 🟢 免费 ⚪ 6大联赛 ⚪ 2014至今

**核心数据字段**

- **球队 xG / xGA（每场）** `(teamsData → xG, xGA per match)` — 可自行计算赛季均值和近N场均值
- **PPDA（逼抢强度）** `(teamsData → ppda · ppda_allowed)` — FootyStats 没有，这是 Understat 独有
- **球员 NPxG / xA** `(playersData → npxg, xA, npg)` — 非点球预期进球，未来球员模块核心
- **比赛级 xG 时间线** `(match/{id} → shotsData → 每次射门xG值)` — 可重建比赛xG累积图
- **滚动控球 xG 趋势** `(teamsData → xG rolling / deep)` — 识别球队近期进攻趋势
- **历史赛季数据** `(/league/season/* 全部历史)` — 可回溯到2014年

#### // 接入方式：页面内嵌 JSON 提取
- **原理**: Understat 将数据以`JSON.parse('...')`形式嵌入 HTML <script> 标签，无需模拟浏览器，直接用`requests`抓取页面后用正则提取
- **示例代码**: `r = requests.get("https://understat.com/league/EPL/2024")``data = re.findall(r"teamsData.*?JSON.parse\('(.+?)'\)", r.text)``teams = json.loads(data[0].encode().decode('unicode_escape'))`
- **反爬措施**: 基本无限制，加 User-Agent 即可。建议请求间隔 1-2 秒避免触发频率限制
- **现有工具**: `understatapi`PyPI 包已封装全部端点，直接 pip install 即可

#### // 开发可行性评估
- **接入难度**: 9/10 (92%)
- **数据质量**: 9/10 (90%)
- **稳定性**: 7.5/10 (75%)
- **成本效益**: 10/10 (100%)

  - PyPI 包understatapi已存在，5 分钟内可集成
  - 无官方 API，页面结构改变会导致解析失败；需维护检测脚本
  - 仅覆盖六大联赛，无法扩展到其他赛事
  - 最高优先级引入：同时解决 PPDA 缺口和未来球员模块需求，且完全免费

---

### ClubElo

**URL**: clubelo.com/API

专门维护欧洲俱乐部 Elo 评分的免费数据库。提供简洁的 CSV API，可获取任意球队任意日期的历史 Elo 值。

🟢 官方 API（CSV格式） 🟢 完全免费 ⚪ 欧洲主流联赛

**核心数据字段**

- **当前 Elo 评分** `(GET /TeamName → 最新 Elo 值)` — v3.0 第一层直接使用
- **历史 Elo 序列** `(GET /TeamName/YYYY-MM-DD → 历史任意日期)` — 回测时还原历史时点的实力对比
- **当日所有球队快照** `(GET /YYYY-MM-DD → 全部球队 Elo)` — 可批量拉取，建本地缓存

#### // 接入方式
- **端点格式**: `http://api.clubelo.com/Chelsea`→ 返回 CSV，一行即当前 Elo
- **示例**: `import pandas as pd``df = pd.read_csv("http://api.clubelo.com/Manchester-City")``elo_now = df.iloc[-1]['Elo']`
- **注意**: 球队名称格式为连字符形式（`Manchester-City`），需维护一份别名映射表与 FootyStats 球队名对齐

#### // 开发可行性评估
- **接入难度**: 10/10 (98%)
- **数据质量**: 8/10 (80%)
- **稳定性**: 8.5/10 (85%)

  - 3 行代码完成接入，几乎零开发成本
  - 唯一维护工作：建立球队名称映射表（约 100 个球队，一次性工作）
  - Elo 更新有 1-2 天延迟；当前轮次刚结束时数据可能未刷新

---

### FBref（StatsBomb 数据）

**URL**: fbref.com

StatsBomb 驱动的免费统计平台，包含高级战术统计（PPDA、progressive passes、pressure data）。HTML 表格可直接用 pandas 解析，但有速率限制。

🟡 HTML 表格抓取 🟢 免费 ⚪ 五大联赛 + 欧冠 🔴 速率限制严格

**核心数据字段**

- **PPDA（逼抢效率）** `(squad-stats → misc → PPDA)` — FootyStats 缺口；第四层节奏模型核心
- **Progressive Passes/Carries** `(squad-stats → passing → Prog)` — 直接进攻比例的代理指标
- **Pressure 数据** `(misc → Press, PressSucc %)` — 逼抢成功率，补充 PPDA
- **球员 NPxG+xA** `(player-stats → npxg, xA per 90)` — 未来球员模块备用来源

#### // 接入方式
- **方法**: `pandas.read_html(url)`直接解析 HTML 表格，无需解析器
- **速率限制**: 严格限速，建议请求间隔5 秒以上，否则会被 429 封禁（临时）。每日抓取建议在非高峰时段运行
- **现有库**: `soccerdata`Python 包封装了 FBref 抓取并处理速率限制，推荐使用而非自行编写
- **缓存策略**: 赛季统计数据每周更新一次即可，不需要每次分析都重新抓取。建议本地 SQLite 缓存

#### // 开发可行性评估
- **接入难度**: 6/10 (60%)
- **数据质量**: 9/10 (92%)
- **稳定性**: 6/10 (60%)

  - 速率限制是最大障碍；批量抓取需要设计合理的 sleep 策略
  - 建议用soccerdata库而非自行编写，它已处理好速率和缓存
  - 仅用于抓取 PPDA 一个字段时，每赛季一次全量抓取即可，之后本地缓存复用
  - 实用策略：每周一次全量更新写入本地数据库，分析时从库读取，不实时抓取

---

### OddsPortal

**URL**: oddsportal.com

最全的历史赔率聚合平台，支持赔率变动时间线追踪。是精明资金信号的关键数据来源，但无官方 API，需要使用 Selenium 或 Playwright 抓取 JavaScript 渲染页面。

🟡 JS渲染页面 需Playwright 🟢 免费浏览 🔴 反爬措施中等 ⚪ 40+ 博彩公司

**核心数据字段**

- **开盘赔率（多家博彩）** `(odds history → opening odds)` — 比 FootyStats 更多博彩公司对比
- **赔率变动时间线** `(odds history → timestamps + odds values)` — 第三层精明资金信号核心数据
- **即时赔率（赛前最新）** `(当前赔率快照)` — 与开盘对比计算移动幅度
- **大小球 / 亚盘赔率** `(O/U · Asian Handicap tabs)` — 未来扩展模块

#### // 接入方式：Playwright 无头浏览器
- **为何需要**: OddsPortal 用 React 渲染，纯 requests 只能拿到空壳，需要执行 JavaScript
- **推荐方案**: `playwright`Python 库（比 Selenium 更快更稳定）pip install `playwright` && `playwright` install chromium
- **反爬对策**: 随机 User-Agent、模拟滚动行为、请求间隔 3-5 秒、必要时用代理 IP 池
- **开发工作量**: 编写稳定的抓取脚本约需 3-5 天，包括错误处理和重试机制。后期维护成本中等（页面结构偶尔改变）
- **替代方案**: 升级到The Odds API（$15+/月）可完全规避抓取问题，获得稳定 JSON API

#### // 开发可行性评估
- **接入难度**: 4/10 (40%)
- **数据质量**: 9/10 (90%)
- **稳定性**: 5/10 (50%)

  - 数据本身极有价值，但工程成本高；页面结构可能随时改变导致脚本失效
  - 建议策略：MVP 阶段手动查赔率，系统稳定后再投入开发或直接订阅 The Odds API
  - 历史赔率（回测用）比实时赔率更容易抓取，可优先实现

---

### The Odds API

**URL**: the-odds-api.com

专门的赔率聚合 API，支持实时赔率和历史赔率查询，可替代 OddsPortal 的手动操作。有免费额度，付费计划按请求次数计费。

🟢 官方 REST API 🟢 免费额度 500次/月 🟡 $15+/月（付费） ⚪ 40+ 博彩公司

**核心数据字段**

- **实时 1X2 赔率** `(/v4/sports/soccer_*/odds → markets h2h)` — 多家博彩实时数据
- **历史赔率快照** `(/v4/sports/*/odds-history)` — 付费计划才有；用于回测
- **大小球赔率** `(markets: totals)` — O/U 2.5 赔率
- **亚盘（部分支持）** `(markets: asian_handicap)` — 覆盖范围不如 OddsPortal

#### // 接入方式
- **认证**: URL 参数`?apiKey=YOUR_KEY`
- **主端点**: `GET /v4/sports/soccer_epl/odds?regions=eu&markets=h2h&bookmakers=pinnacle`
- **免费额度**: 每月 500 次免费请求，5大联赛每轮约 50 场，够用于手动触发模式（每场分析前调用一次）

#### // 开发可行性评估
- **接入难度**: 9/10 (92%)
- **数据质量**: 8.5/10 (85%)
- **成本效益**: 7.5/10 (75%)

  - OddsPortal 手动抓取的最佳付费替代品；一旦需要自动化即切换此 API
  - 免费额度对于按需（每场赛前查询）完全足够，不需要付费套餐起步

---

### Transfermarkt

**URL**: transfermarkt.com

全球最权威的球员转会和伤病数据库。伤病记录更新及时，覆盖范围广，是自动化获取伤病/停赛数据的最佳免费来源。

🟡 HTML 抓取 🟢 免费 🟡 反爬中等 ⚪ 全球覆盖

**核心数据字段**

- **当前伤病名单** `(/vereins-name/verletzte-spieler/verein/ID)` — 球员、伤病类型、预计复出时间
- **停赛名单** `(同一页面，gesperrte-spieler)` — 红牌/累积黄牌停赛
- **球员市场价值** `(player profile → market value)` — 可作为"核心球员"判断的代理

#### // 接入方式
- **现有库**: `transfermarkt-scraper`PyPI 包已实现主要功能，包括伤病名单抓取
- **反爬**: 需设置合法的`User-Agent`（模拟浏览器），避免高频请求。建议每次分析前只查询本场两支球队，不做批量
- **数据时效**: 伤病数据通常在官方通报后 6-12 小时内更新，不适合赛前 1 小时临阵查询

#### // 开发可行性评估
- **接入难度**: 6.5/10 (65%)
- **数据质量**: 8.5/10 (85%)
- **稳定性**: 6.5/10 (65%)

  - 现有 PyPI 库大幅降低开发成本，约 1 天可完成集成
  - 德语 URL 结构（verletzte-spieler）需要维护球队 ID 映射
  - 最重要的伤病（赛前 24-48 小时内公布）在此平台更新最快

---

### FotMob

**URL**: fotmob.com

提供最快的官方首发阵容数据（官宣后分钟级更新）。无公开 API，社区通过逆向工程发现了内部 API 端点，但存在法律和稳定性风险。

🔴 无官方API 🔴 逆向API（法律风险） 🟢 数据本身免费 🔴 随时可能失效

**核心数据字段**

- **官方首发阵容** `(matchDetails → lineup → confirmed)` — v3.0 零层和第六层唯一可靠来源
- **阵型** `(lineup → formation)` — 第二层战术变化判断
- **首发预测（赛前）** `(lineup → predicted（官宣前）)` — 可用于第二层赛前分析

#### // 接入方式对比
- **方案A（推荐）**: 手动查看 App：开球前 1 小时打开 FotMob App，手动复制首发信息粘贴到分析系统。安全、可靠、零开发成本
- **方案B（谨慎）**: 社区发现的非公开端点：`GET https://www.fotmob.com/api/matchDetails?matchId=*`无需认证，但属于未授权访问，违反 ToS，可能随时被封锁
- **方案C（替代）**: LiveScore.com也提供首发数据，抓取难度相对较低，可作为备用来源

#### // 开发可行性评估
- **技术难度**: 7/10 (70%)
- **法律风险**: 高 (75%)
- **稳定性**: 3/10 (30%)

  - 结论：不建议开发自动化工具。手动方案是唯一合理选择
  - 首发阵容每场只需输入一次（开球前），手动操作约 2 分钟，不值得为此承担技术和法律风险
  - 未来若需自动化，应等待有合法阵容 API 的商业方案（如 SportsMonks、API-Football）

---

### OpenWeatherMap

**URL**: openweathermap.org/api

标准天气 API，提供比赛城市的赛前天气预报。免费套餐每分钟 60 次调用，足以覆盖所有分析场景。

🟢 官方 API 🟢 免费额度充足 ⚪ 全球覆盖

**需要的字段**

- **风速（m/s）** `(wind.speed)` — >8m/s 影响长传和任意球
- **降水量（mm）** `(rain.1h)` — 大雨影响技术型打法
- **天气状况** `(weather[0].main)` — Rain/Clear/Snow 等分类

#### // 接入方式（极简）
- **端点**: `GET /data/2.5/forecast?lat={lat}&lon={lon}&appid=KEY`
- **集成工作量**: 约 20 行代码，输入比赛城市坐标，输出天气对 xG 的调整值（±0 或 -0.10）

#### // 开发可行性评估
- **接入难度**: 10/10 (98%)
- **对模型影响**: 低 (25%)

  - 开发成本极低，但对模型影响也极小（仅室外恶劣天气才触发 -0.10 xG 调整）
  - 适合在其他数据源集成稳定后作为最后一步附加

---

### BBC Sport

**URL**: bbc.com/sport/football

伤病和赛前新闻的最快英文来源，但 HTML 结构不稳定，自动化抓取维护成本高。建议手动查看为主。

🔴 HTML抓取（结构不稳定） 🟢 免费 ⚪ 主要覆盖英超

#### // 可行性评估
- **接入难度**: 3/10 (30%)
- **维护成本**: 高 (80%)

  - 结论：不建议自动化，改用 Transfermarkt 处理伤病，Claude web search 处理新闻
  - BBC 结构改变频繁，维护成本远超收益

### Betfair Exchange API

**URL**: developer.betfair.com

唯一提供真实市场流动性和成交量数据的来源。需要注册 Betfair 账户并通过开发者申请，数据价值极高但门槛较高。

🟢 官方 API 🔴 需账户认证 🔴 英国居民限制 🟡 未来高级功能

#### // 可行性评估
- **接入难度**: 3.5/10 (35%)
- **数据价值**: 9.5/10 (95%)

  - 账户开通需要英国/爱尔兰居民资质；部分地区有地理限制
  - 结论：v3.0 当前阶段不需要。系统成熟后作为精明资金信号的终极数据源

**推荐实施路线**

| 阶段 | 引入数据源 | 实现方式 | 预计工期 | 月成本 |
| --- | --- | --- | --- | --- |
| Phase 1 · MVP | FootyStats + ClubElo + The Odds API（免费额度） | 官方 API，直接集成 | 3–5 天 | £30 |
| Phase 1 · 手动补充 | FotMob（阵容）+ OddsPortal（赔率变动）+ Transfermarkt（伤病） | 人工查看，粘贴输入 | 0 | £0 |
| Phase 2 · 自动化 | Understat（xG/PPDA）+ Transfermarkt 自动化 | Python 抓取 + 本地数据库缓存 | 1–2 周 | £0 |
| Phase 2 · 升级 | The Odds API（付费）替代 OddsPortal 手动 | API 替换，1 天完成 | 1 天 | +$15 |
| Phase 3 · 高级 | FBref（高级战术统计）+ OpenWeatherMap | soccerdata 库 + 轻量 API | 3–5 天 | £0 |
| Phase 4 · 专业 | Betfair Exchange（成交量/精明资金） | 官方 API，需账户认证 | TBD | TBD |