"""
Sportmonks + Understat データ解析器

データ覆盖：
  xG:       Sportmonks expected_goals → Understat → league_avg  ✅
  近況:      缺失                                                  ✗
  積分榜:    Sportmonks get_standings_by_season                  ✅
  赔率:      Sportmonks get_prematch_odds                        ✅
  赔率变动:  Sportmonks get_odds_movement                        ✅
  阵容:      Sportmonks get_fixture_by_id(lineups)               ✅
  H2H:       Sportmonks get_head_to_head                        ✅
"""

import asyncio
from typing import Optional, List, TYPE_CHECKING, Any

from utils.cache import cache_get, cache_set
from utils.logger import logger
from data_strategy.resolver import ResolvedData, CACHE_TTL, _is_error_response, _find_team
from data_strategy.quality import assess_standings_quality, assess_odds_quality
from data_strategy.models import get_understat_league_code

if TYPE_CHECKING:
    from provider.sportmonks.client import SportmonksProvider
    from provider.understat.client import UnderstatProvider


_ODDS_MOVEMENT_WINDOW_HOURS = 48  # Sportmonks provides ~48h of pre-match odds history


class SportmonksResolver:

    def __init__(
        self,
        sportmonks: "SportmonksProvider",
        understat: "UnderstatProvider",
    ) -> None:
        self._sm = sportmonks
        self._us = understat

    async def resolve_xg(
        self,
        home_team: str,
        away_team: str,
        league: str,
        season: str,
        home_team_id: str,
        away_team_id: str,
    ) -> ResolvedData:
        """
        xG fallback chain: sportmonks_direct → understat_direct → league_avg.

        Sportmonks provides per-fixture xG via /expected/fixtures?participant_id=<team_id>.
        We average across recent fixtures to get a stable season estimate.
        """
        cache_key = f"sm_xg_{home_team}_{away_team}_{league}_{season}"
        cached = cache_get("sm_xg", cache_key)
        if cached:
            return ResolvedData(
                data=cached["data"],
                source=cached["source"],
                quality=cached["quality"],
            )

        # ── Step 1: Sportmonks native xG (highest priority) ─────────
        try:
            home_xg_raw, away_xg_raw = await asyncio.gather(
                self._sm.get_expected_goals_by_team(int(home_team_id)),
                self._sm.get_expected_goals_by_team(int(away_team_id)),
                return_exceptions=True,
            )
            home_xg = _extract_team_xg_avg(home_xg_raw)
            away_xg = _extract_team_xg_avg(away_xg_raw)

            if home_xg is not None and away_xg is not None:
                data = {
                    "home_xg_for": home_xg["xg_for"],
                    "home_xg_against": home_xg["xg_against"],
                    "away_xg_for": away_xg["xg_for"],
                    "away_xg_against": away_xg["xg_against"],
                }
                # Validate: reject if both teams return all-zero (API returns data but no values)
                total = sum(data.values())
                if total > 0:
                    result = ResolvedData(data=data, source="sportmonks_direct", quality=0.90)
                    cache_set(
                        "sm_xg",
                        cache_key,
                        {"data": data, "source": "sportmonks_direct", "quality": 0.90},
                        ttl_hours=CACHE_TTL["xg"],
                    )
                    return result
                logger.warning(
                    f"[SportmonksResolver] xG returned all zeros for {home_team} vs {away_team}, falling back"
                )
        except Exception as exc:
            logger.warning(f"[SportmonksResolver] Sportmonks xG error: {exc}")

        # ── Step 2: Understat fallback ───────────────────────────────
        understat_code = get_understat_league_code(league)
        if understat_code:
            try:
                teams = await self._us.get_league_teams(understat_code, season)
                if teams:
                    home_s = _find_team(teams, home_team)
                    away_s = _find_team(teams, away_team)
                    if home_s and away_s:
                        data = {
                            "home_xg_for": float(home_s.get("xG", 0) or 0),
                            "home_xg_against": float(home_s.get("xGA", 0) or 0),
                            "away_xg_for": float(away_s.get("xG", 0) or 0),
                            "away_xg_against": float(away_s.get("xGA", 0) or 0),
                        }
                        # Reject all-zero Understat responses (future fixtures not yet played)
                        if sum(data.values()) > 0:
                            result = ResolvedData(
                                data=data, source="understat_direct", quality=0.85
                            )
                            cache_set(
                                "sm_xg",
                                cache_key,
                                {"data": data, "source": "understat_direct", "quality": 0.85},
                                ttl_hours=CACHE_TTL["xg"],
                            )
                            return result
                        logger.warning(
                            f"[SportmonksResolver] Understat returned all zeros for {home_team} vs {away_team}"
                        )
            except Exception as exc:
                logger.warning(f"[SportmonksResolver] Understat xG error: {exc}")

        # ── Step 3: League average (lowest priority) ─────────────────
        return ResolvedData(
            data={"fallback": "league_avg"}, source="league_avg", quality=0.35
        )

    async def resolve_form(
        self, home_team_id: str, away_team_id: str
    ) -> ResolvedData:
        """Sportmonks has no last_x_stats equivalent — always missing."""
        return ResolvedData.missing("form")

    async def resolve_standings(self, season_id: str) -> ResolvedData:
        cache_key = f"sm_standings_{season_id}"
        cached = cache_get("sm_standings", cache_key)
        if cached:
            return ResolvedData(
                data=cached["data"],
                source=cached["source"],
                quality=cached["quality"],
            )

        try:
            raw = await self._sm.get_standings_by_season(int(season_id))
            if raw and not _is_error_response(raw):
                data = {"raw": raw}
                quality = assess_standings_quality(raw, raw, source="sportmonks")
                result = ResolvedData(data=data, source="sportmonks", quality=quality)
                cache_set(
                    "sm_standings",
                    cache_key,
                    {"data": data, "source": "sportmonks", "quality": quality},
                    ttl_hours=CACHE_TTL["standings"],
                )
                return result
        except Exception as exc:
            logger.error(f"[SportmonksResolver] Standings error: {exc}")

        return ResolvedData.missing("standings")

    async def resolve_odds(self, match_id: str) -> ResolvedData:
        cache_key = f"sm_odds_{match_id}"
        cached = cache_get("sm_odds", cache_key)
        if cached:
            return ResolvedData(
                data=cached["data"],
                source=cached["source"],
                quality=cached["quality"],
            )

        try:
            raw = await self._sm.get_prematch_odds(int(match_id))
            if raw and not _is_error_response(raw):
                odds_data = _extract_sportmonks_odds_local(raw)
                if odds_data:
                    quality = assess_odds_quality(odds_data, source="sportmonks")
                    if quality > 0:
                        result = ResolvedData(
                            data=odds_data, source="sportmonks", quality=quality
                        )
                        cache_set(
                            "sm_odds",
                            cache_key,
                            {"data": odds_data, "source": "sportmonks", "quality": quality},
                            ttl_hours=CACHE_TTL["odds"],
                        )
                        return result
        except Exception as exc:
            logger.warning(f"[SportmonksResolver] Odds error: {exc}")

        return ResolvedData.missing("odds")

    async def resolve_lineups(
        self, fixture_id: str, home_team_id: str, away_team_id: str
    ) -> ResolvedData:
        cache_key = f"sm_lineups_{fixture_id}"
        cached = cache_get("sm_lineups", cache_key)
        if cached:
            return ResolvedData(
                data=cached["data"],
                source=cached["source"],
                quality=cached["quality"],
            )

        try:
            raw = await self._sm.get_fixture_by_id(int(fixture_id), include="lineups")
            lineups_data = _extract_lineups(raw, home_team_id, away_team_id)
            if lineups_data:
                result = ResolvedData(
                    data=lineups_data, source="sportmonks", quality=0.90
                )
                cache_set(
                    "sm_lineups",
                    cache_key,
                    {"data": lineups_data, "source": "sportmonks", "quality": 0.90},
                    ttl_hours=CACHE_TTL["lineups"],
                )
                return result
        except Exception as exc:
            logger.warning(f"[SportmonksResolver] Lineups error: {exc}")

        return ResolvedData.missing("lineups")

    async def resolve_odds_movement(self, fixture_id: str) -> ResolvedData:
        cache_key = f"sm_odds_mv_{fixture_id}"
        cached = cache_get("sm_odds_mv", cache_key)
        if cached:
            return ResolvedData(
                data=cached["data"],
                source=cached["source"],
                quality=cached["quality"],
            )

        try:
            raw = await self._sm.get_odds_movement(int(fixture_id))
            data = _extract_odds_movement(raw)
            if data:
                result = ResolvedData(data=data, source="sportmonks", quality=0.85)
                cache_set(
                    "sm_odds_mv",
                    cache_key,
                    {"data": data, "source": "sportmonks", "quality": 0.85},
                    ttl_hours=CACHE_TTL["odds"],
                )
                return result
        except Exception as exc:
            logger.warning(f"[SportmonksResolver] Odds movement error: {exc}")

        return ResolvedData.missing("odds_movement")

    async def resolve_head_to_head(
        self, home_team_id: str, away_team_id: str
    ) -> ResolvedData:
        cache_key = f"sm_h2h_{home_team_id}_{away_team_id}"
        cached = cache_get("sm_h2h", cache_key)
        if cached:
            return ResolvedData(
                data=cached["data"],
                source=cached["source"],
                quality=cached["quality"],
            )

        try:
            raw = await self._sm.get_head_to_head(int(home_team_id), int(away_team_id))
            entries = _extract_h2h(raw)
            if entries:
                data = {"entries": entries}
                result = ResolvedData(data=data, source="sportmonks", quality=0.80)
                cache_set(
                    "sm_h2h",
                    cache_key,
                    {"data": data, "source": "sportmonks", "quality": 0.80},
                    ttl_hours=CACHE_TTL["h2h"],
                )
                return result
        except Exception as exc:
            logger.warning(f"[SportmonksResolver] H2H error: {exc}")

        return ResolvedData.missing("head_to_head")


# ── Private helpers ─────────────────────────────────────────


def _extract_team_xg_avg(raw: Any) -> Optional[dict]:
    """
    Parse Sportmonks /expected/fixtures response for a single team.

    Returns {"xg_for": float, "xg_against": float} as season averages,
    or None if the response is unusable (error, empty, or exception object).

    Sportmonks returns per-fixture xG entries; we average across all fixtures
    to get a stable season estimate. Each entry may contain:
      - "xg" or "expected_goals": the team's xG in that fixture
      - "xga" or "expected_goals_against": xGA in that fixture
    """
    if raw is None or isinstance(raw, Exception):
        return None
    if not isinstance(raw, dict):
        return None

    data = raw.get("data", [])
    if not isinstance(data, list) or not data:
        return None

    xg_values: list[float] = []
    xga_values: list[float] = []

    for entry in data:
        if not isinstance(entry, dict):
            continue
        # Sportmonks v3 field names vary by subscription tier
        xg_val = (
            entry.get("xg")
            or entry.get("expected_goals")
            or entry.get("value")  # some tiers nest under "value"
        )
        xga_val = (
            entry.get("xga")
            or entry.get("expected_goals_against")
        )
        try:
            if xg_val is not None:
                xg_values.append(float(xg_val))
            if xga_val is not None:
                xga_values.append(float(xga_val))
        except (TypeError, ValueError):
            continue

    if not xg_values:
        return None

    return {
        "xg_for": sum(xg_values) / len(xg_values),
        "xg_against": sum(xga_values) / len(xga_values) if xga_values else 0.0,
    }


def _extract_sportmonks_odds_local(raw: Any) -> Optional[dict]:
    data = (
        raw.get("data", [])
        if isinstance(raw, dict)
        else (raw if isinstance(raw, list) else [])
    )
    for item in data:
        if not isinstance(item, dict):
            continue
        odds = item.get("odds") or item
        home = float(odds.get("home") or odds.get("dp3") or 0)
        draw = float(odds.get("draw") or odds.get("dp1") or 0)
        away = float(odds.get("away") or odds.get("dp2") or 0)
        if home > 1.0 and draw > 1.0 and away > 1.0:
            return {"home_win": home, "draw": draw, "away_win": away}
    return None


def _extract_lineups(
    raw: Any, home_team_id: str, away_team_id: str
) -> Optional[dict]:
    if not raw or not isinstance(raw, dict):
        return None
    lineups = raw.get("data", {}).get("lineups", [])
    if not lineups:
        return None

    home = next(
        (lu for lu in lineups if str(lu.get("team_id", "")) == str(home_team_id)), {}
    )
    away = next(
        (lu for lu in lineups if str(lu.get("team_id", "")) == str(away_team_id)), {}
    )

    if not home and not away:
        return None

    return {
        "home_formation": home.get("formation"),
        "away_formation": away.get("formation"),
        "home_confirmed": bool(home.get("confirmed", False)),
        "away_confirmed": bool(away.get("confirmed", False)),
    }


def _extract_odds_movement(raw: Any) -> Optional[dict]:
    if not raw or not isinstance(raw, dict):
        return None
    data = raw.get("data", [])
    if not data:
        return None

    def _type_name(entry: dict) -> str:
        t = entry.get("type", {})
        return str(t.get("name", "") if isinstance(t, dict) else "")

    home_vals = [
        float(e.get("value") or 0)
        for e in data
        if isinstance(e, dict) and "Home" in _type_name(e)
    ]
    draw_vals = [
        float(e.get("value") or 0)
        for e in data
        if isinstance(e, dict) and "Draw" in _type_name(e)
    ]
    away_vals = [
        float(e.get("value") or 0)
        for e in data
        if isinstance(e, dict) and "Away" in _type_name(e)
    ]

    if not home_vals or not draw_vals or not away_vals:
        return None
    if home_vals[0] <= 1.0:
        return None

    return {
        "home_open": home_vals[0],
        "home_current": home_vals[-1],
        "draw_open": draw_vals[0],
        "draw_current": draw_vals[-1],
        "away_open": away_vals[0],
        "away_current": away_vals[-1],
        "movement_hours": _ODDS_MOVEMENT_WINDOW_HOURS,
    }


def _extract_h2h(raw: Any) -> List[dict]:
    if not raw or not isinstance(raw, dict):
        return []
    data = raw.get("data", [])
    entries = []
    for match in data[:5]:  # last 5 meetings
        if not isinstance(match, dict):
            continue
        date = (match.get("starting_at") or "")[:10]
        participants = match.get("participants", [])
        home_team = next(
            (
                p["name"]
                for p in participants
                if isinstance(p, dict)
                and isinstance(p.get("meta"), dict)
                and p["meta"].get("location") == "home"
            ),
            "",
        )
        away_team = next(
            (
                p["name"]
                for p in participants
                if isinstance(p, dict)
                and isinstance(p.get("meta"), dict)
                and p["meta"].get("location") == "away"
            ),
            "",
        )
        scores = match.get("scores", [])
        home_goals = sum(
            s["score"]["goals"]
            for s in scores
            if isinstance(s, dict)
            and isinstance(s.get("score"), dict)
            and s["score"].get("participant") == "home"
        )
        away_goals = sum(
            s["score"]["goals"]
            for s in scores
            if isinstance(s, dict)
            and isinstance(s.get("score"), dict)
            and s["score"].get("participant") == "away"
        )
        if home_team and away_team:
            entries.append(
                {
                    "date": date,
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                }
            )
    return entries
