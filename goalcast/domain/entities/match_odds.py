from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class BookmakerOdds:
    """单家博彩公司赔率"""
    bookmaker: str
    home_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None
    over_25_odds: Optional[float] = None
    under_25_odds: Optional[float] = None
    btts_yes_odds: Optional[float] = None
    btts_no_odds: Optional[float] = None


@dataclass
class PinnacleOdds:
    """Pinnacle 赔率（精明资金基准）"""
    home: float = 0.0
    draw: float = 0.0
    away: float = 0.0

    implied_prob_home: float = 0.0
    implied_prob_draw: float = 0.0
    implied_prob_away: float = 0.0

    @property
    def has_valid_odds(self) -> bool:
        return all([self.home > 0, self.draw > 0, self.away > 0])

    def calculate_implied_probabilities(self):
        """计算隐含概率（去 Vig）"""
        if self.has_valid_odds:
            margin = (1/self.home + 1/self.draw + 1/self.away)
            self.implied_prob_home = (1/self.home) / margin
            self.implied_prob_draw = (1/self.draw) / margin
            self.implied_prob_away = (1/self.away) / margin


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
    - 双方进球盘口
    - 双选赔率
    - 半场赔率
    - 角球赔率
    - 零封赔率
    - Pinnacle 赔率（精明资金基准）
    - 多家博彩公司赔率对比
    """
    match_id: int

    odds_home: Optional[float] = None
    odds_draw: Optional[float] = None
    odds_away: Optional[float] = None

    implied_prob_home: float = 0.0
    implied_prob_draw: float = 0.0
    implied_prob_away: float = 0.0

    over_25_odds: Optional[float] = None
    under_25_odds: Optional[float] = None
    over_35_odds: Optional[float] = None
    under_35_odds: Optional[float] = None
    btts_yes_odds: Optional[float] = None
    btts_no_odds: Optional[float] = None

    handicap: Optional[float] = None
    handicap_home_odds: Optional[float] = None
    handicap_away_odds: Optional[float] = None

    odds_doublechance_1x: Optional[float] = None
    odds_doublechance_x2: Optional[float] = None
    odds_doublechance_12: Optional[float] = None

    odds_1st_half_result_1: Optional[float] = None
    odds_1st_half_result_x: Optional[float] = None
    odds_1st_half_result_2: Optional[float] = None

    odds_2nd_half_result_1: Optional[float] = None
    odds_2nd_half_result_x: Optional[float] = None
    odds_2nd_half_result_2: Optional[float] = None

    odds_win_to_nil_1: Optional[float] = None
    odds_win_to_nil_2: Optional[float] = None

    odds_team_a_cs_yes: Optional[float] = None
    odds_team_a_cs_no: Optional[float] = None
    odds_team_b_cs_yes: Optional[float] = None
    odds_team_b_cs_no: Optional[float] = None

    odds_corners_over_75: Optional[float] = None
    odds_corners_over_85: Optional[float] = None
    odds_corners_over_95: Optional[float] = None
    odds_corners_over_105: Optional[float] = None
    odds_corners_over_115: Optional[float] = None
    odds_corners_under_75: Optional[float] = None
    odds_corners_under_85: Optional[float] = None
    odds_corners_under_95: Optional[float] = None
    odds_corners_1: Optional[float] = None
    odds_corners_x: Optional[float] = None
    odds_corners_2: Optional[float] = None

    odds_1st_half_over05: Optional[float] = None
    odds_1st_half_over15: Optional[float] = None
    odds_1st_half_over25: Optional[float] = None
    odds_1st_half_under05: Optional[float] = None
    odds_1st_half_under15: Optional[float] = None
    odds_1st_half_under25: Optional[float] = None

    odds_2nd_half_over05: Optional[float] = None
    odds_2nd_half_over15: Optional[float] = None
    odds_2nd_half_over25: Optional[float] = None
    odds_2nd_half_under05: Optional[float] = None
    odds_2nd_half_under15: Optional[float] = None
    odds_2nd_half_under25: Optional[float] = None

    odds_comparison: Optional[Dict[str, Dict]] = None

    pinnacle_odds: Optional[PinnacleOdds] = None

    extra: Optional[dict] = None

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}
        if self.pinnacle_odds is None:
            self.pinnacle_odds = PinnacleOdds()

    def calculate_implied_probabilities(self):
        """计算隐含概率"""
        if self.odds_home and self.odds_draw and self.odds_away:
            margin = (1/self.odds_home + 1/self.odds_draw + 1/self.odds_away)
            self.implied_prob_home = (1/self.odds_home) / margin
            self.implied_prob_draw = (1/self.odds_draw) / margin
            self.implied_prob_away = (1/self.odds_away) / margin

    def extract_pinnacle_odds(self, odds_comparison: Dict):
        """从赔率对比中提取 Pinnacle 赔率"""
        ft_result = odds_comparison.get("FT Result", {})
        home_data = ft_result.get("Home", {})
        draw_data = ft_result.get("Draw", {})
        away_data = ft_result.get("Away", {})

        pinnacle_home = home_data.get("Pinnacle")
        pinnacle_draw = draw_data.get("Pinnacle")
        pinnacle_away = away_data.get("Pinnacle")

        if pinnacle_home and pinnacle_draw and pinnacle_away:
            try:
                self.pinnacle_odds = PinnacleOdds(
                    home=float(pinnacle_home),
                    draw=float(pinnacle_draw),
                    away=float(pinnacle_away)
                )
                self.pinnacle_odds.calculate_implied_probabilities()
            except (ValueError, TypeError):
                pass

    @property
    def has_full_1x2_odds(self) -> bool:
        return all([self.odds_home, self.odds_draw, self.odds_away])

    @property
    def has_btts_odds(self) -> bool:
        return self.btts_yes_odds is not None and self.btts_no_odds is not None

    @property
    def has_over_25_odds(self) -> bool:
        return self.over_25_odds is not None and self.under_25_odds is not None

    @property
    def has_corners_odds(self) -> bool:
        return self.odds_corners_over_95 is not None

    @property
    def has_ht_odds(self) -> bool:
        return self.odds_1st_half_result_1 is not None

    @property
    def has_pinnacle_odds(self) -> bool:
        return self.pinnacle_odds is not None and self.pinnacle_odds.has_valid_odds