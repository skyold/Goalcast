"""Sportmonks 原始数据采集层。"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from datasource.datafusion.resolvers.sportmonks_resolver import (
    _build_sportmonks_xg_payload,
    _extract_h2h,
    _extract_lineups,
    _extract_sportmonks_asian_handicap_local,
    _extract_odds_movement,
    _extract_sportmonks_odds_local,
)


class SportmonksCollector:
    """封装 provider 调用，返回供 snapshot 组装的原始分层数据。"""

    def __init__(self, provider: Any):
        self.provider = provider

    async def get_fixtures_by_date(self, date: str) -> list[dict]:
        raw = await self.provider.get_fixtures_by_date(date, include="participants;league")
        data = raw.get("data", []) if isinstance(raw, dict) else []
        return [item for item in data if isinstance(item, dict)]

    async def get_all_leagues(self) -> list[dict]:
        """获取全量联赛数据（处理分页）。"""
        all_leagues = []
        page = 1
        while True:
            raw = await self.provider.get_leagues(page=page)
            if not raw or "data" not in raw:
                break
            
            data = raw["data"]
            if not data:
                break
                
            all_leagues.extend(data)
            
            pagination = raw.get("pagination", {})
            if not pagination.get("has_more", False):
                break
            page += 1
        return all_leagues

    async def collect_match_layers(self, fixture: dict) -> dict[str, Any]:
        fixture_id = int(fixture["id"])
        season_id = fixture.get("season_id")
        participants = fixture.get("participants", [])
        home = next(
            (
                p for p in participants
                if isinstance(p, dict) and isinstance(p.get("meta"), dict)
                and p["meta"].get("location") == "home"
            ),
            {},
        )
        away = next(
            (
                p for p in participants
                if isinstance(p, dict) and isinstance(p.get("meta"), dict)
                and p["meta"].get("location") == "away"
            ),
            {},
        )
        home_id = int(home.get("id", 0) or 0)
        away_id = int(away.get("id", 0) or 0)

        fixture_with_lineups, standings_raw, odds_raw, predictions_raw, xg_home_raw, xg_away_raw, h2h_raw = await asyncio.gather(
            self.provider.get_fixture_by_id(
                fixture_id,
                include="lineups;xGFixture;lineups.xGLineup",
            ),
            self.provider.get_standings_by_season(int(season_id)) if season_id else _return_none(),
            self._get_prematch_odds(fixture_id),
            self.provider.get_predictions_by_fixture(fixture_id),
            self.provider.get_expected_goals_by_team(home_id) if home_id else _return_none(),
            self.provider.get_expected_goals_by_team(away_id) if away_id else _return_none(),
            self.provider.get_head_to_head(home_id, away_id) if home_id and away_id else _return_none(),
            return_exceptions=True,
        )

        odds_movement_raw = None
        if hasattr(self.provider, "get_odds_movement"):
            try:
                odds_movement_raw = await self.provider.get_odds_movement(fixture_id)
            except Exception:
                odds_movement_raw = None

        fixture_payload = (
            fixture_with_lineups.get("data")
            if isinstance(fixture_with_lineups, dict) and isinstance(fixture_with_lineups.get("data"), dict)
            else fixture
        )
        xg = _build_sportmonks_xg_payload(
            fixture_with_lineups,
            home_id,
            away_id,
            home_history_raw=xg_home_raw,
            away_history_raw=xg_away_raw,
        )

        return {
            "fixture": fixture_payload,
            "standings": standings_raw if isinstance(standings_raw, dict) else None,
            "odds": _extract_sportmonks_odds_local(odds_raw),
            "asian_handicap": _extract_sportmonks_asian_handicap_local(odds_raw),
            "odds_movement": _extract_odds_movement(odds_movement_raw),
            "lineups": _extract_lineups(fixture_with_lineups, str(home_id), str(away_id)),
            "h2h": _extract_h2h(h2h_raw) if isinstance(h2h_raw, dict) else None,
            "predictions": (predictions_raw or {}).get("data") if isinstance(predictions_raw, dict) else None,
            "xg": xg,
        }

    async def _get_prematch_odds(self, fixture_id: int) -> Any:
        if hasattr(self.provider, "get_prematch_odds"):
            return await self.provider.get_prematch_odds(fixture_id)
        if hasattr(self.provider, "get_prematch_odds_by_fixture"):
            return await self.provider.get_prematch_odds_by_fixture(fixture_id)
        return None


async def _return_none() -> None:
    return None
