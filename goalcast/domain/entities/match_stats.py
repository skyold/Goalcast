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

    home_shots_on_target: int = -1
    away_shots_on_target: int = -1
    home_shots_off_target: int = -1
    away_shots_off_target: int = -1
    home_total_shots: int = -1
    away_total_shots: int = -1

    home_possession: int = -1
    away_possession: int = -1

    home_corners: int = -1
    away_corners: int = -1
    total_corners: int = 0

    home_offsides: int = -1
    away_offsides: int = -1

    home_fouls: int = -1
    away_fouls: int = -1

    home_yellow_cards: int = 0
    away_yellow_cards: int = 0
    home_red_cards: int = 0
    away_red_cards: int = 0

    btts: bool = False
    over_15: bool = False
    over_25: bool = False
    over_35: bool = False
    winning_team_id: Optional[int] = None

    extra: dict = None

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}

    @property
    def has_valid_stats(self) -> bool:
        """判断是否有有效的统计数据"""
        return self.home_possession != -1