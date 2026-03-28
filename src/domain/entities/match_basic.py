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
    match_id: int
    season_id: int
    competition_name: Optional[str] = None

    home_team_id: int = 0
    away_team_id: int = 0
    home_team_name: Optional[str] = None
    away_team_name: Optional[str] = None

    match_time: Optional[datetime] = None
    date_unix: Optional[int] = None
    status: str = 'incomplete'

    home_score: int = 0
    away_score: int = 0
    half_time_home: int = 0
    half_time_away: int = 0

    game_week: Optional[int] = None
    round_id: Optional[int] = None
    venue: Optional[str] = None

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