# Match Data Datasource & Provider Layer Specification

## 文档信息

- **创建日期**: 2026-03-28
- **状态**: Draft
- **作者**: [待填写]
- **审核者**: [待填写]
- **文件名**: `prediction_datasource_spec.md` (保持不变，便于引用)

---

## 1. 概述

### 1.1 目标

本 spec 定义 Goalcast 项目中**比赛数据**的 Datasource 层和 Provider 层架构，支持用户按类别获取比赛相关数据。

### 1.2 核心设计原则

1. **按需数据获取**: 用户通过独立命令获取不同类别的数据，无固定顺序
2. **数据分类组织**: 按数据类别（基础、统计、高级、赔率、球队、其他）组织
3. **API 完整性**: 支持 FootyStats 所有 16 个端点
4. **扩展性**: 数据结构为未来特征值和模型预留空间
5. **最小调用**: 只在用户明确需要时才调用对应 API

### 1.3 使用场景

```
用户操作流程:
1. 浏览比赛列表 → get_schedule 获取赛程
2. 根据需要选择特定比赛 → 使用不同命令获取各类数据
   ├── get_match_basic <match_id> → 比赛基础信息
   ├── get_match_stats <match_id> → 比赛统计数据
   ├── get_match_advanced <match_id> → 高级分析数据
   ├── get_match_odds <match_id> → 赔率数据
   ├── get_match_teams <match_id> → 球队数据
   └── get_match_others <match_id> → 其他补充数据
3. 综合判断 → 未来可接入预测模型
```

---

## 2. 架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      CMD Layer (命令行)                      │
│  - 用户交互入口                                              │
│  - 独立命令调用不同类别数据                                   │
├─────────────────────────────────────────────────────────────┤
│                    Datasource 层                              │
│  - MatchDataDataSource                                       │
│    ├── 按数据类别组织数据获取方法                              │
│    ├── 计算衍生数据（球队状态等）                            │
│    └── 返回分类的数据对象                                    │
├─────────────────────────────────────────────────────────────┤
│                     Provider 层                              │
│  - FootyStatsProvider (现有)                                 │
│    ├── 封装所有 16 个 API 端点                                 │
│    ├── 统一错误处理和日志                                    │
│    └── 数据验证和重试                                        │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据分类定义

| 数据类别 | 数据来源 | 用途 | 数据量 |
|----------|----------|------|--------|
| **Basic** | Today's Matches / Match Details | 基础赛程 | ~500B |
| **Stats** | Match Details | 赛后统计 | ~2KB |
| **Advanced** | Match Details | 深度分析 | ~10KB |
| **Odds** | Match Details | 赔率对比 | ~5KB |
| **Teams** | Team/LastX/League Teams | 球队状态 | ~8KB |
| **Others** | 其他 API | 完整信息 | ~15KB |

---

## 3. Provider 层设计

### 3.1 现有 Provider 分析

**文件位置**: `/Users/zhengningdai/workspace/skyold/Goalcast/src/provider/footystats/client.py`

**现有端点**（16 个）:
```python
# 基础端点
- get_league_list()
- get_country_list()
- get_todays_matches()

# 联赛数据端点
- get_league_stats()
- get_league_matches()
- get_league_teams()
- get_league_players()
- get_league_referees()
- get_league_tables()

# 详细数据端点
- get_match_details()
- get_team()
- get_team_last_x_stats()
- get_player_stats()
- get_referee_stats()

# 统计数据端点
- get_btts_stats()
- get_over_2_5_stats()
```

### 3.2 Provider 层改进建议

**不需要修改 Provider 层**，保持现有 API 封装，由 Datasource 层负责组合调用。

**原因**:
1. Provider 层已完整覆盖 16 个端点
2. 单一职责：Provider 只负责 API 调用
3. 组合逻辑应在 Datasource 层

---

## 4. Datasource 层设计

### 4.1 核心类结构

```python
# 文件：src/datasource/footystats/match_datasource.py

class MatchDataDataSource:
    """
    比赛数据源
    
    职责:
    1. 按数据类别组织数据获取
    2. 聚合多个 Provider 调用
    3. 计算衍生数据（如球队状态）
    4. 返回分类的数据对象
    """
    
    def __init__(self, provider: FootyStatsProvider):
        self.provider = provider
    
    # 数据类别获取方法
    async def get_match_basic(self, match_id: int) -> MatchBasicData
    async def get_match_stats(self, match_id: int) -> MatchStatsData
    async def get_match_advanced(self, match_id: int) -> MatchAdvancedData
    async def get_match_odds(self, match_id: int) -> MatchOddsData
    async def get_match_teams(self, match_id: int) -> MatchTeamsData
    async def get_match_others(self, match_id: int) -> MatchOthersData
    
    # 完整数据获取（用于未来模型）
    async def get_full_match_data(self, match_id: int) -> FullMatchData
```

### 4.2 数据实体设计

#### 4.2.1 基础数据

```python
# 文件：src/domain/entities/match_basic.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class MatchBasicData:
    """
    比赛基础数据
    
    来源：Today's Matches API / League Matches API
    用途：比赛列表、赛程展示
    数据量：~500 字节
    """
    # 标识
    match_id: int
    season_id: int  # 联赛赛季 ID
    competition_name: Optional[str] = None
    
    # 球队
    home_team_id: int
    away_team_id: int
    home_team_name: Optional[str] = None
    away_team_name: Optional[str] = None
    
    # 时间
    match_time: Optional[datetime] = None
    date_unix: Optional[int] = None
    status: str = 'incomplete'  # incomplete, inprogress, complete
    
    # 比分（未开始时为 0）
    home_score: int = 0
    away_score: int = 0
    half_time_home: int = 0
    half_time_away: int = 0
    
    # 基础信息
    game_week: Optional[int] = None
    round_id: Optional[int] = None
    venue: Optional[str] = None  # 球场
    
    # 扩展字段（为未来预留）
    extra: dict = None
    
    def __post_init__(self):
        if self.extra is None:
            self.extra = {}
    
    @property
    def is_finished(self) -> bool:
        return self.status == 'complete'
    
    @property
    def is_live(self) -> bool:
        return self.status == 'inprogress'
```

---

#### 4.2.2 统计数据

```python
# 文件：src/domain/entities/match_stats.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class MatchStatsData:
    """
    比赛统计数据
    
    来源：League Matches API
    用途：赛后统计分析
    数据量：~2KB
    
    包含：
    - 基础统计（射门、角球、控球率）
    - 纪律数据（黄牌、红牌）
    - 标记（BTTS、Over 2.5 等）
    """
    match_id: int
    
    # 射门统计
    home_shots_on_target: int = -1
    away_shots_on_target: int = -1
    home_shots_off_target: int = -1
    away_shots_off_target: int = -1
    home_total_shots: int = -1
    away_total_shots: int = -1
    
    # 控球率
    home_possession: int = -1
    away_possession: int = -1
    
    # 角球
    home_corners: int = -1
    away_corners: int = -1
    total_corners: int = 0
    
    # 越位
    home_offsides: int = -1
    away_offsides: int = -1
    
    # 犯规
    home_fouls: int = -1
    away_fouls: int = -1
    
    # 纪律
    home_yellow_cards: int = 0
    away_yellow_cards: int = 0
    home_red_cards: int = 0
    away_red_cards: int = 0
    
    # 标记
    btts: bool = False  # 双方进球
    over_15: bool = False
    over_25: bool = False
    over_35: bool = False
    winning_team_id: Optional[int] = None  # -1 表示平局
    
    # 扩展字段
    extra: dict = None
    
    def __post_init__(self):
        if self.extra is None:
            self.extra = {}
    
    @property
    def has_valid_stats(self) -> bool:
        """判断是否有有效的统计数据"""
        return self.home_possession != -1
```

---

#### 4.2.3 高级数据

```python
# 文件：src/domain/entities/match_advanced.py

from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class LineupPlayer:
    """首发球员"""
    player_id: int
    shirt_number: int
    events: List[Dict] = field(default_factory=list)


@dataclass
class MatchAdvancedData:
    """
    比赛高级分析数据
    
    来源：Match Details API
    用途：深度分析、预测特征
    数据量：~10KB
    
    包含：
    - 高级统计（xG、进攻次数）
    - 阵容信息
    - 交锋记录
    - 趋势分析
    - 天气信息
    """
    match_id: int
    
    # 高级统计
    home_xg: Optional[float] = None  # 期望进球
    away_xg: Optional[float] = None
    total_xg: Optional[float] = None
    
    home_attacks: Optional[int] = None  # 进攻次数
    away_attacks: Optional[int] = None
    home_dangerous_attacks: Optional[int] = None
    away_dangerous_attacks: Optional[int] = None
    
    # 阵容
    home_lineup: List[LineupPlayer] = field(default_factory=list)
    away_lineup: List[LineupPlayer] = field(default_factory=list)
    home_bench: List[Dict] = field(default_factory=list)
    away_bench: List[Dict] = field(default_factory=list)
    
    # 交锋记录（简化版，详细版在 Layer 5）
    h2h_summary: Optional[Dict] = None
    
    # 趋势分析
    home_trends: List[str] = field(default_factory=list)
    away_trends: List[str] = field(default_factory=list)
    
    # 天气
    weather: Optional[Dict] = None
    
    # 裁判
    referee_id: Optional[int] = None
    
    # 扩展字段
    extra: dict = None
    
    def __post_init__(self):
        if self.extra is None:
            self.extra = {}
    
    @property
    def has_xg(self) -> bool:
        return self.home_xg is not None and self.home_xg > 0
    
    @property
    def has_lineups(self) -> bool:
        return len(self.home_lineup) > 0 and len(self.away_lineup) > 0
```

---

#### 4.2.4 赔率数据

```python
# 文件：src/domain/entities/match_odds.py

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class MatchOddsData:
    """
    比赛赔率数据
    
    来源：Today's Matches API / Match Details API
    用途：赔率分析、价值投注识别
    数据量：~5KB
    
    包含：
    - 基础赔率（胜平负）
    - 亚洲盘口
    - 大小球盘口
    - 赔率对比（多家博彩公司）
    """
    match_id: int
    
    # 基础赔率（FT Result）
    odds_home: Optional[float] = None
    odds_draw: Optional[float] = None
    odds_away: Optional[float] = None
    
    # 隐含概率
    implied_prob_home: float = 0.0
    implied_prob_draw: float = 0.0
    implied_prob_away: float = 0.0
    
    # 大小球
    over_25_odds: Optional[float] = None
    under_25_odds: Optional[float] = None
    btts_yes_odds: Optional[float] = None
    btts_no_odds: Optional[float] = None
    
    # 让球盘（简化）
    handicap: Optional[float] = None
    handicap_home_odds: Optional[float] = None
    handicap_away_odds: Optional[float] = None
    
    # 赔率对比（多家博彩公司）
    odds_comparison: Optional[Dict[str, Dict]] = None
    
    # 扩展字段
    extra: dict = None
    
    def __post_init__(self):
        if self.extra is None:
            self.extra = {}
    
    def calculate_implied_probabilities(self):
        """计算隐含概率"""
        if self.odds_home and self.odds_draw and self.odds_away:
            margin = (1/self.odds_home + 1/self.odds_draw + 1/self.odds_away)
            self.implied_prob_home = (1/self.odds_home) / margin
            self.implied_prob_draw = (1/self.odds_draw) / margin
            self.implied_prob_away = (1/self.odds_away) / margin
```

---

#### 4.2.5 球队数据

```python
# 文件：src/domain/entities/match_teams.py

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class TeamForm:
    """
    球队状态
    
    从最近比赛计算得出
    """
    team_id: int
    
    # 近 5 场统计
    last_5_matches: int = 0
    last_5_wins: int = 0
    last_5_draws: int = 0
    last_5_losses: int = 0
    last_5_points: int = 0
    last_5_ppg: float = 0.0
    last_5_goals_scored: int = 0
    last_5_goals_conceded: int = 0
    
    # 连胜/连败
    current_streak: int = 0  # 正=连胜，负=连败
    current_streak_type: str = ''  # win/draw/loss
    
    # 趋势
    btts_percentage: float = 0.0
    over_25_percentage: float = 0.0


@dataclass
class TeamSeasonStats:
    """
    球队赛季统计
    """
    team_id: int
    season_id: int
    
    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_scored: int = 0
    goals_conceded: int = 0
    points: int = 0
    ppg: float = 0.0
    position: int = 0
    
    avg_goals_scored: float = 0.0
    avg_goals_conceded: float = 0.0
    avg_xg: float = 0.0
    avg_xga: float = 0.0


@dataclass
class MatchTeamsData:
    """
    比赛球队数据
    
    来源：Team API / LastX API / League Teams API
    用途：球队状态分析、预测特征
    数据量：~8KB
    
    包含：
    - 球队状态（近况）
    - 赛季统计
    - 主客场表现
    - 详细交锋记录
    """
    match_id: int
    home_team_id: int
    away_team_id: int
    
    # 球队状态
    home_form: Optional[TeamForm] = None
    away_form: Optional[TeamForm] = None
    
    # 赛季统计
    home_season_stats: Optional[TeamSeasonStats] = None
    away_season_stats: Optional[TeamSeasonStats] = None
    
    # 主客场分离统计
    home_home_stats: Optional[TeamSeasonStats] = None  # 主场战绩
    away_away_stats: Optional[TeamSeasonStats] = None  # 客场战绩
    
    # 交锋记录
    h2h_total: int = 0
    h2h_home_wins: int = 0
    h2h_away_wins: int = 0
    h2h_draws: int = 0
    h2h_avg_goals: float = 0.0
    h2h_btts_percentage: float = 0.0
    
    # 扩展字段
    extra: dict = None
    
    def __post_init__(self):
        if self.extra is None:
            self.extra = {}
    
    @property
    def form_difference(self) -> float:
        """状态差异（主队 - 客队）"""
        if self.home_form and self.away_form:
            return self.home_form.last_5_ppg - self.away_form.last_5_ppg
        return 0.0
    
    @property
    def strength_difference(self) -> float:
        """实力差异"""
        if self.home_season_stats and self.away_season_stats:
            return self.home_season_stats.ppg - self.away_season_stats.ppg
        return 0.0
```

---

#### 4.2.6 其他数据

```python
# 文件：src/domain/entities/match_others.py

from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class MatchOthersData:
    """
    比赛其他补充数据
    
    来源：Various APIs
    用途：完整信息展示、特殊分析
    数据量：~15KB
    
    包含：
    - 球员数据
    - 裁判数据
    - 联赛统计
    - BTTS/Over 2.5 统计
    """
    match_id: int
    
    # 球员数据（可选）
    home_top_scorers: List[Dict] = field(default_factory=list)
    away_top_scorers: List[Dict] = field(default_factory=list)
    
    # 裁判数据
    referee_stats: Optional[Dict] = None
    
    # 联赛统计（该比赛的联赛）
    league_stats: Optional[Dict] = None
    
    # BTTS 统计
    btts_league_stats: Optional[Dict] = None
    
    # Over 2.5 统计
    over_25_league_stats: Optional[Dict] = None
    
    # 扩展字段
    extra: dict = None
    
    def __post_init__(self):
        if self.extra is None:
            self.extra = {}
```

---

#### 4.2.7 完整比赛数据（未来扩展）

```python
# 文件：src/domain/entities/full_match_data.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class FullMatchData:
    """
    完整比赛数据
    
    聚合所有数据类别的数据，用于未来 ML 模型预测
    
    设计原则：
    - 组合而非继承
    - 保留各类数据的独立性
    - 为特征工程预留接口
    """
    match_id: int
    
    # 各类数据
    basic: Optional[MatchBasicData] = None
    stats: Optional[MatchStatsData] = None
    advanced: Optional[MatchAdvancedData] = None
    odds: Optional[MatchOddsData] = None
    teams: Optional[MatchTeamsData] = None
    others: Optional[MatchOthersData] = None
    
    # 衍生特征（未来用于 ML）
    features: dict = None
    
    # 预测结果（未来由模型生成）
    prediction: dict = None
    
    def __post_init__(self):
        if self.features is None:
            self.features = {}
        if self.prediction is None:
            self.prediction = {}
    
    @property
    def is_complete(self) -> bool:
        """判断是否所有类别数据都已加载"""
        return all([
            self.basic is not None,
            self.stats is not None,
            self.advanced is not None,
            self.odds is not None,
            self.teams is not None,
        ])
    
    def to_feature_vector(self) -> dict:
        """
        转换为特征向量（未来 ML 使用）
        
        TODO: 实现特征工程逻辑
        """
        features = {}
        
        # TODO: 从各类数据中提取特征
        # - Basic: 基础信息
        # - Stats: 统计数据
        # - Advanced: 高级统计
        # - Odds: 赔率数据
        # - Teams: 球队状态
        
        return features
```

---

### 4.3 Datasource 实现

```python
# 文件：src/datasource/footystats/match_datasource.py

from typing import Optional, List
from datetime import date, datetime

from provider.footystats.client import FootyStatsProvider
from domain.entities.match_basic import MatchBasicData
from domain.entities.match_stats import MatchStatsData
from domain.entities.match_advanced import MatchAdvancedData, LineupPlayer
from domain.entities.match_odds import MatchOddsData
from domain.entities.match_teams import MatchTeamsData, TeamForm, TeamSeasonStats
from domain.entities.match_others import MatchOthersData
from domain.entities.full_match_data import FullMatchData
from utils.logger import logger


class MatchDataDataSource:
    """
    比赛数据源
    
    设计理念:
    1. 按数据类别组织数据获取
    2. 只获取用户需要的数据
    3. 计算衍生数据（如球队状态）
    4. 为未来 ML 预留接口
    """
    
    def __init__(self, provider: FootyStatsProvider):
        self.provider = provider
    
    # ==================== 数据类别获取方法 ====================
    
    async def get_match_basic(self, match_id: int) -> Optional[MatchBasicData]:
        """
        获取比赛基础数据
        
        调用策略:
        1. 先从 Today's Matches 查找（如果日期匹配）
        2. 否则从 League Matches 获取
        
        Returns:
            MatchBasicData 或 None
        """
        logger.debug(f"Datasource: get_match_basic(match_id={match_id})")
        
        # 策略：先尝试从 Match Details 获取基础信息
        # 因为 Match Details 总是可用的
        result = await self.provider.get_match_details(match_id)
        
        if not result or not result.get('success'):
            logger.error(f"Failed to get match details for {match_id}")
            return None
        
        data = result.get('data', {})
        
        # 转换为 MatchBasicData
        return self._parse_basic_data(data)
    
    async def get_match_stats(self, match_id: int) -> Optional[MatchStatsData]:
        """
        获取比赛统计数据
        
        来源：Match Details API（包含完整统计）
        
        Returns:
            MatchStatsData 或 None
        """
        logger.debug(f"Datasource: get_match_stats(match_id={match_id})")
        
        result = await self.provider.get_match_details(match_id)
        if not result or not result.get('success'):
            return None
        
        data = result.get('data', {})
        return self._parse_stats_data(data)
    
    async def get_match_advanced(self, match_id: int) -> Optional[MatchAdvancedData]:
        """
        获取高级分析数据
        
        来源：Match Details API
        
        Returns:
            MatchAdvancedData 或 None
        """
        logger.debug(f"Datasource: get_match_advanced(match_id={match_id})")
        
        result = await self.provider.get_match_details(match_id)
        if not result or not result.get('success'):
            return None
        
        data = result.get('data', {})
        return self._parse_advanced_data(data)
    
    async def get_match_odds(self, match_id: int) -> Optional[MatchOddsData]:
        """
        获取赔率数据
        
        来源：Match Details API（包含完整赔率对比）
        
        Returns:
            MatchOddsData 或 None
        """
        logger.debug(f"Datasource: get_match_odds(match_id={match_id})")
        
        result = await self.provider.get_match_details(match_id)
        if not result or not result.get('success'):
            return None
        
        data = result.get('data', {})
        odds_data = self._parse_odds_data(data)
        
        # 计算隐含概率
        if odds_data:
            odds_data.calculate_implied_probabilities()
        
        return odds_data
    
    async def get_match_teams(self, match_id: int) -> Optional[MatchTeamsData]:
        """
        获取球队数据
        
        来源：
        - Team API: 球队详情
        - LastX API: 球队近况
        - League Teams API: 赛季统计
        
        Returns:
            MatchTeamsData 或 None
        """
        logger.debug(f"Datasource: get_match_teams(match_id={match_id})")
        
        # Step 1: 先获取比赛基础信息，拿到球队 ID
        basic_data = await self.get_match_basic(match_id)
        if not basic_data:
            return None
        
        home_team_id = basic_data.home_team_id
        away_team_id = basic_data.away_team_id
        season_id = basic_data.season_id
        
        # Step 2: 获取球队状态（LastX API）
        home_form = await self._get_team_form(home_team_id)
        away_form = await self._get_team_form(away_team_id)
        
        # Step 3: 获取赛季统计（League Teams API）
        home_season_stats = await self._get_team_season_stats(home_team_id, season_id)
        away_season_stats = await self._get_team_season_stats(away_team_id, season_id)
        
        # Step 4: 获取交锋记录（从 Match Details）
        h2h_data = await self._get_h2h_data(match_id)
        
        # Step 5: 组装 MatchTeamsData
        teams_data = MatchTeamsData(
            match_id=match_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_form=home_form,
            away_form=away_form,
            home_season_stats=home_season_stats,
            away_season_stats=away_season_stats,
        )
        
        # 填充交锋记录
        if h2h_data:
            teams_data.h2h_total = h2h_data.get('total_matches', 0)
            teams_data.h2h_home_wins = h2h_data.get('home_wins', 0)
            teams_data.h2h_away_wins = h2h_data.get('away_wins', 0)
            teams_data.h2h_draws = h2h_data.get('draws', 0)
            teams_data.h2h_avg_goals = h2h_data.get('avg_goals', 0.0)
            teams_data.h2h_btts_percentage = h2h_data.get('btts_pct', 0.0)
        
        return teams_data
    
    async def get_match_others(self, match_id: int) -> Optional[MatchOthersData]:
        """
        获取其他补充数据
        
        来源：Various APIs
        
        Returns:
            MatchOthersData 或 None
        """
        logger.debug(f"Datasource: get_match_others(match_id={match_id})")
        
        # 获取比赛信息
        basic_data = await self.get_match_basic(match_id)
        if not basic_data:
            return None
        
        season_id = basic_data.season_id
        
        others_data = MatchOthersData(match_id=match_id)
        
        # TODO: 根据需要获取其他数据
        # - 球员数据
        # - 裁判数据
        # - 联赛统计
        
        return others_data
    
    async def get_full_match_data(self, match_id: int) -> Optional[FullMatchData]:
        """
        获取完整比赛数据（聚合所有类别）
        
        Returns:
            FullMatchData 或 None
        """
        logger.debug(f"Datasource: get_full_match_data(match_id={match_id})")
        
        full_data = FullMatchData(match_id=match_id)
        
        # 按顺序获取各类数据
        full_data.basic = await self.get_match_basic(match_id)
        if not full_data.basic:
            return None
        
        full_data.stats = await self.get_match_stats(match_id)
        full_data.advanced = await self.get_match_advanced(match_id)
        full_data.odds = await self.get_match_odds(match_id)
        full_data.teams = await self.get_match_teams(match_id)
        full_data.others = await self.get_match_others(match_id)
        
        return full_data
    
    # ==================== 辅助方法 ====================
    
    def _parse_basic_data(self, data: dict) -> MatchBasicData:
        """解析基础数据"""
        from datetime import datetime
        
        match_time = None
        if data.get('date_unix'):
            match_time = datetime.fromtimestamp(data['date_unix'])
        
        return MatchBasicData(
            match_id=data.get('id', 0),
            season_id=data.get('competition_id', 0),
            competition_name=None,  # TODO: 从联赛列表获取
            home_team_id=data.get('homeID', 0),
            away_team_id=data.get('awayID', 0),
            home_team_name=data.get('home_name'),
            away_team_name=data.get('away_name'),
            match_time=match_time,
            date_unix=data.get('date_unix'),
            status=data.get('status', 'incomplete'),
            home_score=data.get('homeGoalCount', 0),
            away_score=data.get('awayGoalCount', 0),
            half_time_home=data.get('half_time', {}).get('team_a', 0),
            half_time_away=data.get('half_time', {}).get('team_b', 0),
            game_week=data.get('game_week'),
            round_id=data.get('roundID'),
            venue=data.get('stadium_name'),
        )
    
    def _parse_stats_data(self, data: dict) -> MatchStatsData:
        """解析统计数据"""
        return MatchStatsData(
            match_id=data.get('id', 0),
            home_shots_on_target=data.get('team_a_shotsOnTarget', -1),
            away_shots_on_target=data.get('team_b_shotsOnTarget', -1),
            home_shots_off_target=data.get('team_a_shotsOffTarget', -1),
            away_shots_off_target=data.get('team_b_shotsOffTarget', -1),
            home_total_shots=data.get('team_a_shots', -1),
            away_total_shots=data.get('team_b_shots', -1),
            home_possession=data.get('team_a_possession', -1),
            away_possession=data.get('team_b_possession', -1),
            home_corners=data.get('team_a_corners', -1),
            away_corners=data.get('team_b_corners', -1),
            total_corners=data.get('totalCornerCount', 0),
            home_offsides=data.get('team_a_offsides', -1),
            away_offsides=data.get('team_b_offsides', -1),
            home_fouls=data.get('team_a_fouls', -1),
            away_fouls=data.get('team_b_fouls', -1),
            home_yellow_cards=data.get('team_a_yellow_cards', 0),
            away_yellow_cards=data.get('team_b_yellow_cards', 0),
            home_red_cards=data.get('team_a_red_cards', 0),
            away_red_cards=data.get('team_b_red_cards', 0),
            btts=data.get('btts', False),
            over_15=data.get('over15', False),
            over_25=data.get('over25', False),
            over_35=data.get('over35', False),
            winning_team_id=data.get('winningTeam'),
        )
    
    def _parse_advanced_data(self, data: dict) -> MatchAdvancedData:
        """解析高级数据"""
        advanced = MatchAdvancedData(
            match_id=data.get('id', 0),
            home_xg=data.get('team_a_xg'),
            away_xg=data.get('team_b_xg'),
            total_xg=data.get('total_xg'),
            home_attacks=data.get('team_a_attacks'),
            away_attacks=data.get('team_b_attacks'),
            home_dangerous_attacks=data.get('team_a_dangerous_attacks'),
            away_dangerous_attacks=data.get('team_b_dangerous_attacks'),
            referee_id=data.get('refereeID'),
            weather=data.get('weather'),
        )
        
        # 解析阵容
        lineups_data = data.get('lineups', {})
        if lineups_data:
            advanced.home_lineup = [
                LineupPlayer(
                    player_id=p.get('player_id'),
                    shirt_number=p.get('shirt_number'),
                    events=p.get('player_events', [])
                )
                for p in lineups_data.get('team_a', [])
            ]
            advanced.away_lineup = [
                LineupPlayer(
                    player_id=p.get('player_id'),
                    shirt_number=p.get('shirt_number'),
                    events=p.get('player_events', [])
                )
                for p in lineups_data.get('team_b', [])
            ]
        
        # 交锋记录
        h2h_data = data.get('h2h', {})
        if h2h_data:
            advanced.h2h_summary = h2h_data
        
        # 趋势分析
        trends = data.get('trends', {})
        advanced.home_trends = [t[1] for t in trends.get('home', []) if len(t) > 1]
        advanced.away_trends = [t[1] for t in trends.get('away', []) if len(t) > 1]
        
        return advanced
    
    def _parse_odds_data(self, data: dict) -> MatchOddsData:
        """解析赔率数据"""
        odds = MatchOddsData(
            match_id=data.get('id', 0),
            odds_home=data.get('odds_ft_1'),
            odds_draw=data.get('odds_ft_x'),
            odds_away=data.get('odds_ft_2'),
            over_25_odds=data.get('odds_ft_over25'),
            under_25_odds=data.get('odds_ft_under25'),
            btts_yes_odds=data.get('odds_btts_yes'),
            btts_no_odds=data.get('odds_btts_no'),
            odds_comparison=data.get('odds_comparison'),
        )
        
        return odds
    
    async def _get_team_form(self, team_id: int) -> Optional[TeamForm]:
        """获取球队状态（从 LastX API）"""
        try:
            result = await self.provider.get_team_last_x_stats(team_id)
            if not result or not result.get('success'):
                return None
            
            # TODO: 解析 LastX 数据
            # 简化版本，实际需要根据 API 返回解析
            return TeamForm(team_id=team_id)
        except Exception as e:
            logger.error(f"Failed to get team form for {team_id}: {e}")
            return None
    
    async def _get_team_season_stats(self, team_id: int, season_id: int) -> Optional[TeamSeasonStats]:
        """获取球队赛季统计（从 League Teams API）"""
        try:
            result = await self.provider.get_league_teams(season_id)
            if not result or not result.get('success'):
                return None
            
            teams_data = result.get('data', [])
            for team in teams_data:
                if team.get('team_id') == team_id:
                    # TODO: 解析球队统计
                    return TeamSeasonStats(team_id=team_id, season_id=season_id)
            
            return None
        except Exception as e:
            logger.error(f"Failed to get team stats for {team_id}: {e}")
            return None
    
    async def _get_h2h_data(self, match_id: int) -> Optional[dict]:
        """获取交锋记录（从 Match Details API）"""
        try:
            result = await self.provider.get_match_details(match_id)
            if not result or not result.get('success'):
                return None
            
            h2h = result.get('data', {}).get('h2h', {})
            if not h2h:
                return None
            
            prev_results = h2h.get('previous_matches_results', {})
            betting_stats = h2h.get('betting_stats', {})
            
            return {
                'total_matches': prev_results.get('totalMatches', 0),
                'home_wins': prev_results.get('team_a_wins', 0),
                'away_wins': prev_results.get('team_b_wins', 0),
                'draws': prev_results.get('draw', 0),
                'avg_goals': betting_stats.get('avg_goals', 0.0),
                'btts_pct': betting_stats.get('bttsPercentage', 0.0),
            }
        except Exception as e:
            logger.error(f"Failed to get H2H data: {e}")
            return None
    
    # ==================== 比赛列表获取 ====================
    
    async def get_recent_matches(self, days: int = 7) -> List[MatchBasicData]:
        """
        获取最近 N 天的比赛列表
        
        Args:
            days: 天数，默认 7 天
        
        Returns:
            MatchBasicData 列表
        """
        from datetime import timedelta
        
        matches = []
        
        for i in range(days):
            target_date = datetime.now() - timedelta(days=i)
            date_str = target_date.strftime('%Y-%m-%d')
            
            result = await self.provider.get_todays_matches(date=date_str)
            if result and result.get('success'):
                for match_data in result.get('data', []):
                    basic = self._parse_basic_data(match_data)
                    matches.append(basic)
        
        return matches
```

---

## 5. 使用示例

### 5.1 CMD 命令设计

```python
# 文件：src/cmd/match_data_cmd.py

import asyncio
from typing import Optional

from provider.footystats.client import FootyStatsProvider
from datasource.footystats.match_datasource import MatchDataDataSource


class MatchDataCMD:
    """
    比赛数据命令行入口
    
    提供一组独立命令，用户根据需要调用：
    - get_schedule: 获取比赛列表
    - get_match_basic <match_id>: 基础信息
    - get_match_stats <match_id>: 统计数据
    - get_match_advanced <match_id>: 高级数据
    - get_match_odds <match_id>: 赔率数据
    - get_match_teams <match_id>: 球队数据
    - get_match_others <match_id>: 其他数据
    - get_full_match <match_id>: 完整数据
    """
    
    def __init__(self):
        self.provider = FootyStatsProvider()
        self.datasource = MatchDataDataSource(self.provider)
    
    async def get_schedule(self, days: int = 7):
        """获取最近 N 天的比赛列表"""
        matches = await self.datasource.get_recent_matches(days)
        self._print_matches(matches)
    
    async def get_match_basic(self, match_id: int):
        """获取比赛基础信息"""
        data = await self.datasource.get_match_basic(match_id)
        if data:
            self._print_basic(data)
    
    async def get_match_stats(self, match_id: int):
        """获取比赛统计数据"""
        data = await self.datasource.get_match_stats(match_id)
        if data:
            self._print_stats(data)
    
    async def get_match_advanced(self, match_id: int):
        """获取比赛高级数据"""
        data = await self.datasource.get_match_advanced(match_id)
        if data:
            self._print_advanced(data)
    
    async def get_match_odds(self, match_id: int):
        """获取比赛赔率数据"""
        data = await self.datasource.get_match_odds(match_id)
        if data:
            self._print_odds(data)
    
    async def get_match_teams(self, match_id: int):
        """获取比赛球队数据"""
        data = await self.datasource.get_match_teams(match_id)
        if data:
            self._print_teams(data)
    
    async def get_match_others(self, match_id: int):
        """获取比赛其他数据"""
        data = await self.datasource.get_match_others(match_id)
        if data:
            self._print_others(data)
    
    async def get_full_match(self, match_id: int):
        """获取完整比赛数据"""
        data = await self.datasource.get_full_match_data(match_id)
        if data:
            self._print_full(data)
    
    def _print_matches(self, matches):
        """打印比赛列表"""
        print("\n=== 比赛列表 ===")
        for match in matches:
            print(f"[{match.match_id}] {match.home_team_name} vs {match.away_team_name}")
            print(f"  时间：{match.match_time}")
            print(f"  比分：{match.home_score} - {match.away_score}")
            print()
    
    def _print_basic(self, data):
        """打印基础信息"""
        print(f"\n=== 比赛信息 ===")
        print(f"比赛：{data.home_team_name} vs {data.away_team_name}")
        print(f"时间：{data.match_time}")
        print(f"比分：{data.home_score} - {data.away_score}")
        print(f"状态：{data.status}")
        print(f"球场：{data.venue or 'N/A'}")
    
    def _print_stats(self, data):
        """打印统计数据"""
        print(f"\n=== 统计数据 ===")
        if data.has_valid_stats:
            print(f"控球率：{data.home_possession}% - {data.away_possession}%")
            print(f"射门：{data.home_total_shots} - {data.away_total_shots}")
            print(f"射正：{data.home_shots_on_target} - {data.away_shots_on_target}")
            print(f"角球：{data.home_corners} - {data.away_corners}")
            print(f"黄牌：{data.home_yellow_cards} - {data.away_yellow_cards}")
            print(f"BTTS: {'是' if data.btts else '否'}")
            print(f"Over 2.5: {'是' if data.over_25 else '否'}")
        else:
            print("比赛尚未进行或无统计数据")
    
    def _print_advanced(self, data):
        """打印高级数据"""
        print(f"\n=== 高级数据 ===")
        if data.has_xg:
            print(f"xG: {data.home_xg:.2f} - {data.away_xg:.2f}")
            print(f"总 xG: {data.total_xg:.2f}")
        if data.has_lineups:
            print(f"主队首发：{len(data.home_lineup)} 人")
            print(f"客队首发：{len(data.away_lineup)} 人")
        print(f"进攻：{data.home_attacks or 'N/A'} - {data.away_attacks or 'N/A'}")
        print(f"危险进攻：{data.home_dangerous_attacks or 'N/A'} - {data.away_dangerous_attacks or 'N/A'}")
    
    def _print_odds(self, data):
        """打印赔率数据"""
        print(f"\n=== 赔率数据 ===")
        if data.odds_home:
            print(f"主胜：{data.odds_home:.2f} (隐含概率 {data.implied_prob_home:.1%})")
            print(f"平局：{data.odds_draw:.2f} (隐含概率 {data.implied_prob_draw:.1%})")
            print(f"客胜：{data.odds_away:.2f} (隐含概率 {data.implied_prob_away:.1%})")
        if data.over_25_odds:
            print(f"大球 2.5: {data.over_25_odds:.2f}")
            print(f"小球 2.5: {data.under_25_odds:.2f}")
    
    def _print_teams(self, data):
        """打印球队数据"""
        print(f"\n=== 球队数据 ===")
        if data.home_form:
            print(f"主队近 5 场：{data.home_form.last_5_wins}胜{data.home_form.last_5_draws}平{data.home_form.last_5_losses}负")
            print(f"主队场均积分：{data.home_form.last_5_ppg:.2f}")
        if data.away_form:
            print(f"客队近 5 场：{data.away_form.last_5_wins}胜{data.away_form.last_5_draws}平{data.away_form.last_5_losses}负")
            print(f"客队场均积分：{data.away_form.last_5_ppg:.2f}")
        print(f"交锋记录：{data.h2h_total} 场")
        print(f"主队胜：{data.h2h_home_wins} | 客队胜：{data.h2h_away_wins} | 平局：{data.h2h_draws}")
    
    def _print_others(self, data):
        """打印其他数据"""
        print(f"\n=== 其他数据 ===")
        # 根据需要展示
    
    def _print_full(self, data):
        """打印完整数据"""
        self._print_basic(data.basic)
        self._print_stats(data.stats)
        self._print_advanced(data.advanced)
        self._print_odds(data.odds)
        self._print_teams(data.teams)
        self._print_others(data.others)


# CLI 入口
async def main():
    import sys
    
    cmd = MatchDataCMD()
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  match_data get_schedule [days]")
        print("  match_data get_match_basic <match_id>")
        print("  match_data get_match_stats <match_id>")
        print("  match_data get_match_advanced <match_id>")
        print("  match_data get_match_odds <match_id>")
        print("  match_data get_match_teams <match_id>")
        print("  match_data get_match_others <match_id>")
        print("  match_data get_full_match <match_id>")
        return
    
    command = sys.argv[1]
    
    if command == 'get_schedule':
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        await cmd.get_schedule(days)
    elif command == 'get_match_basic':
        match_id = int(sys.argv[2])
        await cmd.get_match_basic(match_id)
    elif command == 'get_match_stats':
        match_id = int(sys.argv[2])
        await cmd.get_match_stats(match_id)
    elif command == 'get_match_advanced':
        match_id = int(sys.argv[2])
        await cmd.get_match_advanced(match_id)
    elif command == 'get_match_odds':
        match_id = int(sys.argv[2])
        await cmd.get_match_odds(match_id)
    elif command == 'get_match_teams':
        match_id = int(sys.argv[2])
        await cmd.get_match_teams(match_id)
    elif command == 'get_match_others':
        match_id = int(sys.argv[2])
        await cmd.get_match_others(match_id)
    elif command == 'get_full_match':
        match_id = int(sys.argv[2])
        await cmd.get_full_match(match_id)
    else:
        print(f"未知命令：{command}")


if __name__ == '__main__':
    asyncio.run(main())
```

### 5.2 使用示例

```bash
# 1. 获取最近 7 天比赛列表
$ python -m src.cmd.match_data_cmd get_schedule

# 2. 获取特定比赛的基础信息
$ python -m src.cmd.match_data_cmd get_match_basic 579101

# 3. 获取统计数据
$ python -m src.cmd.match_data_cmd get_match_stats 579101

# 4. 获取高级数据
$ python -m src.cmd.match_data_cmd get_match_advanced 579101

# 5. 获取赔率数据
$ python -m src.cmd.match_data_cmd get_match_odds 579101

# 6. 获取球队数据
$ python -m src.cmd.match_data_cmd get_match_teams 579101

# 7. 获取完整数据
$ python -m src.cmd.match_data_cmd get_full_match 579101
```

---

## 6. TODO 列表

### 6.1 第一阶段：基础架构

- [ ] 创建数据实体类（6 个 Layer）
- [ ] 实现 PredictionMatchDataSource
- [ ] 实现基础解析方法
- [ ] 编写单元测试

### 6.2 第二阶段：数据完整性

- [ ] 实现所有 16 个 API 端点的调用
- [ ] 完善球队状态计算逻辑
- [ ] 实现交锋记录聚合
- [ ] 添加错误处理和重试

### 6.3 第三阶段：CMD 集成

- [ ] 实现 CMD 命令行界面
- [ ] 实现渐进式数据加载
- [ ] 添加数据展示格式化
- [ ] 用户交互优化

### 6.4 第四阶段：特征工程（未来）

- [ ] 实现特征提取接口
- [ ] 添加特征计算方法
- [ ] 集成 ML 模型
- [ ] 预测结果展示

### 6.5 第五阶段：优化和扩展

- [ ] 实现缓存层
- [ ] 批量数据获取优化
- [ ] 添加数据验证
- [ ] 性能监控

---

## 7. 附录

### 7.1 API 端点映射表

| 数据类别 | 主要 API | 次要 API |
|----------|----------|----------|
| Basic | Match Details | Today's Matches |
| Stats | Match Details | League Matches |
| Advanced | Match Details | - |
| Odds | Match Details | Today's Matches |
| Teams | LastX, League Teams | Team |
| Others | Various | - |

### 7.2 文件结构

```
src/
├── provider/footystats/
│   └── client.py (现有，不变)
├── datasource/footystats/
│   └── match_datasource.py (新建)
├── domain/entities/
│   ├── match_basic.py (新建)
│   ├── match_stats.py (新建)
│   ├── match_advanced.py (新建)
│   ├── match_odds.py (新建)
│   ├── match_teams.py (新建)
│   ├── match_others.py (新建)
│   └── full_match_data.py (新建)
└── cmd/
    └── match_data_cmd.py (新建)
```

---

## 8. 决策记录

### 8.1 为什么按数据类别组织而非 Layer？

**决策**: 按数据类别（Basic、Stats、Advanced 等）组织，而非 Layer 1/2/3

**理由**:
1. 避免暗示先后顺序（用户可自由调用）
2. 更符合数据本质（描述数据内容）
3. 便于理解和记忆
4. 支持独立命令调用

### 8.2 为什么 CMD 使用独立命令而非菜单？

**决策**: 每个数据类别对应一个独立命令

**理由**:
1. 用户完全控制，按需调用
2. 符合 CLI 使用习惯
3. 易于脚本化和自动化
4. 无状态设计，更简洁

### 8.3 为什么不修改 Provider 层？

**决策**: 保持 Provider 层不变

**理由**:
1. Provider 已完整覆盖 16 个端点
2. 单一职责原则
3. 组合逻辑应在 Datasource 层
4. 减少代码变更风险

### 8.4 为什么使用组合而非继承？

**决策**: FullMatchData 组合各类数据

**理由**:
1. 保持各类数据独立性
2. 支持按需加载
3. 避免深层继承链
4. 更易测试和维护
