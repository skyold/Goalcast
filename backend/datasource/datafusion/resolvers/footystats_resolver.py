"""
FootyStats + Understat データ解析器

データ覆盖：
  xG:       Understat → FootyStats proxy → league_avg  ✅
  近況:      FootyStats get_team_last_x_stats           ✅
  積分榜:    FootyStats get_league_tables               ✅
  赔率:      FootyStats match_details（静的のみ）        ✅
  阵容:      缺失（FootyStats 无可靠阵容数据）           ✗
  赔率变动:  缺失                                        ✗
  H2H:       缺失                                        ✗
"""

from typing import TYPE_CHECKING

from datasource.datafusion.resolver import DataResolver, ResolvedData

if TYPE_CHECKING:
    from provider.footystats.client import FootyStatsProvider
    from provider.understat.client import UnderstatProvider


class FootyStatsResolver:
    """
    FootyStats-based resolver. Delegates all data fetching to the existing
    DataResolver. The three Sportmonks-exclusive methods always return missing.
    """

    def __init__(
        self,
        footystats: "FootyStatsProvider",
        understat: "UnderstatProvider",
    ) -> None:
        self._delegate = DataResolver(
            footystats=footystats,
            understat=understat,
        )

    async def resolve_xg(self, **kwargs) -> ResolvedData:
        return await self._delegate.resolve_xg(**kwargs)

    async def resolve_form(
        self, home_team_id: str, away_team_id: str
    ) -> ResolvedData:
        return await self._delegate.resolve_form(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
        )

    async def resolve_standings(self, season_id: str) -> ResolvedData:
        return await self._delegate.resolve_standings(season_id=season_id)

    async def resolve_odds(self, match_id: str) -> ResolvedData:
        return await self._delegate.resolve_odds(match_id=match_id)

    async def resolve_lineups(
        self, fixture_id: str, home_team_id: str, away_team_id: str
    ) -> ResolvedData:
        return ResolvedData.missing("lineups")

    async def resolve_odds_movement(self, fixture_id: str) -> ResolvedData:
        return ResolvedData.missing("odds_movement")

    async def resolve_head_to_head(
        self, home_team_id: str, away_team_id: str
    ) -> ResolvedData:
        return ResolvedData.missing("head_to_head")

    async def resolve_predictions(self, fixture_id: str) -> ResolvedData:
        """FootyStats 官方不提供概率预测。"""
        return ResolvedData.missing("predictions")
