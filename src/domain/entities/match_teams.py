from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class TeamForm:
    """
    球队状态

    从最近比赛计算得出
    """
    team_id: int

    last_5_matches: int = 0
    last_5_wins: int = 0
    last_5_draws: int = 0
    last_5_losses: int = 0
    last_5_points: int = 0
    last_5_ppg: float = 0.0
    last_5_goals_scored: int = 0
    last_5_goals_conceded: int = 0

    current_streak: int = 0
    current_streak_type: str = ''

    btts_percentage: float = 0.0
    over_25_percentage: float = 0.0


@dataclass
class TeamSeasonStats:
    """
    球队赛季统计

    包含：
    - 基本战绩（胜平负、积分、排名）
    - 进球/失球统计
    - xG/xGA 统计
    - 半场数据
    - 主场/客场表现
    - 零封/进球统计
    - 大球/双方进球统计
    - 主场优势指标
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

    xg_for_avg_overall: float = 0.0
    xg_for_avg_home: float = 0.0
    xg_for_avg_away: float = 0.0
    xg_against_avg_overall: float = 0.0
    xg_against_avg_home: float = 0.0
    xg_against_avg_away: float = 0.0

    home_attack_advantage: int = 0
    home_defence_advantage: int = 0
    home_overall_advantage: int = 0

    ht_ppg_overall: float = 0.0
    ht_ppg_home: float = 0.0
    ht_ppg_away: float = 0.0
    leading_at_ht_percentage_overall: float = 0.0
    leading_at_ht_percentage_home: float = 0.0
    leading_at_ht_percentage_away: float = 0.0
    drawing_at_ht_percentage_overall: float = 0.0
    trailing_at_ht_percentage_overall: float = 0.0

    clean_sheet_percentage_overall: float = 0.0
    clean_sheet_percentage_home: float = 0.0
    clean_sheet_percentage_away: float = 0.0
    failed_to_score_percentage_overall: float = 0.0
    btts_percentage_overall: float = 0.0
    btts_percentage_home: float = 0.0
    btts_percentage_away: float = 0.0

    over_25_percentage_overall: float = 0.0
    over_25_percentage_home: float = 0.0
    over_25_percentage_away: float = 0.0
    over_35_percentage_overall: float = 0.0

    highest_scored_home: int = 0
    highest_conceded_home: int = 0
    highest_scored_away: int = 0
    highest_conceded_away: int = 0

    season_goals_total_overall: int = 0
    season_goals_total_home: int = 0
    season_goals_total_away: int = 0
    season_matches_played_home: int = 0
    season_matches_played_away: int = 0

    win_percentage_overall: float = 0.0
    win_percentage_home: float = 0.0
    win_percentage_away: float = 0.0
    draw_percentage_overall: float = 0.0
    draw_percentage_away: float = 0.0
    lose_percentage_overall: float = 0.0
    lose_percentage_home: float = 0.0
    lose_percentage_away: float = 0.0


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
    - 扩展 h2h 统计（进球、大球、双方进球）
    """
    match_id: int
    home_team_id: int
    away_team_id: int

    home_form: Optional[TeamForm] = None
    away_form: Optional[TeamForm] = None

    home_season_stats: Optional[TeamSeasonStats] = None
    away_season_stats: Optional[TeamSeasonStats] = None

    home_home_stats: Optional[TeamSeasonStats] = None
    away_away_stats: Optional[TeamSeasonStats] = None

    h2h_total: int = 0
    h2h_home_wins: int = 0
    h2h_away_wins: int = 0
    h2h_draws: int = 0
    h2h_avg_goals: float = 0.0
    h2h_btts_percentage: float = 0.0

    h2h_over_25_count: int = 0
    h2h_btts_count: int = 0
    h2h_over_25_percentage: float = 0.0
    h2h_total_goals: int = 0

    extra: Optional[dict] = None

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

    @property
    def h2h_home_win_percentage(self) -> float:
        if self.h2h_total > 0:
            return (self.h2h_home_wins / self.h2h_total) * 100
        return 0.0

    @property
    def h2h_away_win_percentage(self) -> float:
        if self.h2h_total > 0:
            return (self.h2h_away_wins / self.h2h_total) * 100
        return 0.0

    @property
    def h2h_draw_percentage(self) -> float:
        if self.h2h_total > 0:
            return (self.h2h_draws / self.h2h_total) * 100
        return 0.0