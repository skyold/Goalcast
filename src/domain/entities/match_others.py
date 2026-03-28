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

    home_top_scorers: List[Dict] = field(default_factory=list)
    away_top_scorers: List[Dict] = field(default_factory=list)

    referee_stats: Optional[Dict] = None

    league_stats: Optional[Dict] = None

    btts_league_stats: Optional[Dict] = None

    over_25_league_stats: Optional[Dict] = None

    extra: dict = None

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}