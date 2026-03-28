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
    - 潜力指标（BTTS、大球概率）
    - 赛前 PPG 数据
    - 阵容信息
    - 交锋记录
    - 趋势分析
    - 天气信息
    """
    match_id: int

    home_xg: Optional[float] = None
    away_xg: Optional[float] = None
    total_xg: Optional[float] = None

    home_xg_prematch: Optional[float] = None
    away_xg_prematch: Optional[float] = None
    total_xg_prematch: Optional[float] = None

    home_attacks: Optional[int] = None
    away_attacks: Optional[int] = None
    home_dangerous_attacks: Optional[int] = None
    away_dangerous_attacks: Optional[int] = None

    home_lineup: List[LineupPlayer] = field(default_factory=list)
    away_lineup: List[LineupPlayer] = field(default_factory=list)
    home_bench: List[Dict] = field(default_factory=list)
    away_bench: List[Dict] = field(default_factory=list)

    h2h_summary: Optional[Dict] = None

    home_trends: List[str] = field(default_factory=list)
    away_trends: List[str] = field(default_factory=list)

    weather: Optional[Dict] = None

    referee_id: Optional[int] = None

    extra: Optional[dict] = None

    btts_potential: Optional[int] = None
    btts_fhg_potential: Optional[int] = None
    btts_2hg_potential: Optional[int] = None
    o25_potential: Optional[int] = None
    o35_potential: Optional[int] = None
    o45_potential: Optional[int] = None
    u25_potential: Optional[int] = None
    u35_potential: Optional[int] = None
    corners_potential: Optional[float] = None
    avg_potential: Optional[float] = None

    pre_match_home_ppg: Optional[float] = None
    pre_match_away_ppg: Optional[float] = None
    pre_match_teamA_overall_ppg: Optional[float] = None
    pre_match_teamB_overall_ppg: Optional[float] = None

    home_ppg: Optional[float] = None
    away_ppg: Optional[float] = None

    h2h_previous_matches: List[Dict] = field(default_factory=list)
    h2h_betting_stats: Optional[Dict] = None

    home_goals_timings: List[str] = field(default_factory=list)
    away_goals_timings: List[str] = field(default_factory=list)

    matches_completed_minimum: Optional[int] = None
    game_week: Optional[int] = None

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}

    @property
    def has_xg(self) -> bool:
        return self.home_xg is not None and self.home_xg > 0

    @property
    def has_xg_prematch(self) -> bool:
        return self.home_xg_prematch is not None and self.home_xg_prematch > 0

    @property
    def has_lineups(self) -> bool:
        return len(self.home_lineup) > 0 and len(self.away_lineup) > 0

    @property
    def xg_difference(self) -> float:
        if self.home_xg_prematch is not None and self.away_xg_prematch is not None:
            return self.home_xg_prematch - self.away_xg_prematch
        return 0.0

    @property
    def total_xg_prematch_sum(self) -> float:
        if self.home_xg_prematch is not None and self.away_xg_prematch is not None:
            return self.home_xg_prematch + self.away_xg_prematch
        return 0.0

    @property
    def ppg_difference(self) -> float:
        if self.home_ppg is not None and self.away_ppg is not None:
            return self.home_ppg - self.away_ppg
        return 0.0