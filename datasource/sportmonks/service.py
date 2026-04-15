"""Sportmonks 独立数据层服务入口。"""

from __future__ import annotations

from datetime import date as date_cls
from typing import Any, Optional

from .models import (
    SportmonksFixtureSummary,
    SportmonksMatchSnapshot,
    SportmonksWarmupResult,
)
from .store import SportmonksStore
from .transformer import build_match_snapshot


_LEAGUE_FILTER_SPECS: dict[str, dict[str, Any]] = {
    "Premier League": {
        "names": {"premier league"},
        "country_ids": {462},
        "short_code_contains": {"eng", "epl"},
    },
    "Championship": {
        "names": {"championship"},
        "country_ids": {462},
        "short_code_contains": {"champ"},
    },
    "Serie A": {
        "names": {"serie a"},
        "short_code_contains": {"ita"},
    },
}


def _matches_requested_leagues(payload: dict[str, Any], requested_leagues: list[str]) -> bool:
    for league_name in requested_leagues:
        if _matches_league(payload, league_name):
            return True
    return False


def _matches_league(payload: dict[str, Any], requested_league: str) -> bool:
    league_info = payload.get("league") if isinstance(payload.get("league"), dict) else payload
    actual_name = str(league_info.get("name") or league_info.get("league_name") or payload.get("league_name") or "").strip()
    actual_name_lower = actual_name.lower()
    country_id = league_info.get("country_id") or payload.get("league_country_id")
    short_code = str(league_info.get("short_code") or payload.get("league_short_code") or "").lower()

    spec = _LEAGUE_FILTER_SPECS.get(requested_league)
    if spec is None:
        return actual_name_lower == requested_league.lower()

    if actual_name_lower not in spec["names"]:
        return False

    if country_id is None and not short_code:
        return True

    country_ids = spec.get("country_ids")
    if country_ids and country_id in country_ids:
        return True

    short_code_contains = spec.get("short_code_contains", set())
    if short_code and any(token in short_code for token in short_code_contains):
        return True

    return False


class SportmonksDataService:
    """协调 today 入口、缓存读取与后续采集刷新逻辑。"""

    def __init__(self, store: Optional[Any] = None, collector: Optional[Any] = None):
        self.store = store or SportmonksStore()
        self.collector = collector
        self._league_index: Optional[dict[int, dict[str, Any]]] = None

    async def sync_leagues(self) -> dict[str, Any]:
        """从 API 同步全量联赛数据并持久化到本地。"""
        if self.collector is None:
            raise RuntimeError("collector is required for sync_leagues()")
        
        leagues = await self.collector.get_all_leagues()
        self.store.write_leagues(leagues)
        self._league_index = {int(l["id"]): l for l in leagues}
        
        return {
            "total_synced": len(leagues),
            "status": "success"
        }

    def _get_league_index(self) -> dict[int, dict[str, Any]]:
        """获取联赛索引（带内存缓存）。"""
        if self._league_index is not None:
            return self._league_index
        
        leagues = self.store.read_leagues()
        self._league_index = {int(l["id"]): l for l in leagues}
        return self._league_index

    def get_leagues_by_name(self, name: str) -> list[dict[str, Any]]:
        """根据名称模糊查找联赛。"""
        index = self._get_league_index()
        name_lower = name.lower()
        return [
            league for league in index.values()
            if name_lower in league.get("name", "").lower()
        ]

    def _matches_requested_leagues(self, payload: dict[str, Any], requested_leagues: list[str]) -> bool:
        for league_name in requested_leagues:
            if self._matches_league(payload, league_name):
                return True
        return False

    def _matches_league(self, payload: dict[str, Any], requested_league: str) -> bool:
        league_info = payload.get("league") if isinstance(payload.get("league"), dict) else payload
        actual_name = str(league_info.get("name") or league_info.get("league_name") or payload.get("league_name") or "").strip()
        actual_name_lower = actual_name.lower()
        league_id = league_info.get("id") or league_info.get("league_id") or payload.get("league_id")
        country_id = league_info.get("country_id") or payload.get("league_country_id")
        short_code = str(league_info.get("short_code") or payload.get("league_short_code") or "").lower()

        # 1. 优先支持 ID 匹配
        if requested_league.isdigit() and league_id:
            if int(requested_league) == int(league_id):
                return True

        # 2. 检查硬编码的 Specs
        spec = _LEAGUE_FILTER_SPECS.get(requested_league)
        if spec:
            if actual_name_lower in spec["names"]:
                if country_id is None and not short_code:
                    return True
                country_ids = spec.get("country_ids")
                if country_ids and country_id in country_ids:
                    return True
                short_code_contains = spec.get("short_code_contains", set())
                if short_code and any(token in short_code for token in short_code_contains):
                    return True

        # 3. 兜底逻辑：完全名称匹配或本地索引匹配
        if actual_name_lower == requested_league.lower():
            return True
            
        # 检查是否是已同步联赛的别名或名称
        index = self._get_league_index()
        for league in index.values():
            if league.get("name", "").lower() == requested_league.lower():
                if int(league["id"]) == int(league_id):
                    return True

        return False

    async def get_todays_matches(
        self,
        leagues: Optional[list[str]] = None,
        warm_if_missing: bool = True,
    ) -> list[SportmonksFixtureSummary]:
        return await self.get_fixtures(
            date=date_cls.today().isoformat(),
            leagues=leagues,
            warm_if_missing=warm_if_missing,
        )

    async def prefetch_today(
        self,
        leagues: Optional[list[str]] = None,
        refresh_stale: bool = False,
    ) -> Any:
        return await self.prefetch(
            date=date_cls.today().isoformat(),
            leagues=leagues,
            refresh_stale=refresh_stale,
        )

    async def get_fixtures(
        self,
        date: str,
        leagues: Optional[list[str]] = None,
        warm_if_missing: bool = True,
    ) -> list[SportmonksFixtureSummary]:
        payloads = self.store.read_fixtures(date)
        if not payloads and warm_if_missing and self.collector is not None:
            await self.prefetch(date=date, leagues=leagues, refresh_stale=False)
            payloads = self.store.read_fixtures(date)
        if leagues:
            payloads = [
                payload for payload in payloads
                if self._matches_requested_leagues(payload, leagues)
            ]
        return [SportmonksFixtureSummary(**payload) for payload in payloads]

    async def prefetch(
        self,
        date: str,
        leagues: Optional[list[str]] = None,
        refresh_stale: bool = False,
    ) -> Any:
        if self.collector is None:
            raise RuntimeError("collector is required for prefetch()")

        fixtures = await self.collector.get_fixtures_by_date(date)
        if leagues:
            fixtures = [
                fixture for fixture in fixtures
                if self._matches_requested_leagues(fixture, leagues)
            ]

        summaries: list[SportmonksFixtureSummary] = []
        warmed = 0
        partial = 0
        failed = 0
        results: list[dict[str, Any]] = []

        for fixture in fixtures:
            try:
                raw_layers = await self.collector.collect_match_layers(fixture)
                snapshot = build_match_snapshot(raw_layers)

                self.store.write_match(
                    fixture_id=snapshot.fixture_id,
                    date=date,
                    snapshot=snapshot.to_dict(),
                    home_team=snapshot.home_team,
                    away_team=snapshot.away_team,
                )
                self.store.write_meta(
                    fixture_id=snapshot.fixture_id,
                    date=date,
                    meta={
                        "fixture_id": snapshot.fixture_id,
                        "cache_status": snapshot.cache_status,
                        "available_layers": list(snapshot.available_layers),
                        "missing_layers": list(snapshot.missing_layers),
                        "updated_at": snapshot.updated_at,
                        "expires_at": snapshot.expires_at,
                    },
                )
                for layer, payload in raw_layers.items():
                    if payload is not None:
                        self.store.write_raw_layer(snapshot.fixture_id, date, layer, payload)

                summary = SportmonksFixtureSummary(
                    fixture_id=snapshot.fixture_id,
                    match_date=snapshot.match_date,
                    kickoff_time=snapshot.kickoff_time,
                    league_id=int((fixture.get("league") or {}).get("id", 0) or 0),
                    league_name=snapshot.league,
                    season_id=snapshot.season_id,
                    home_team_id=snapshot.home_team_id,
                    home_team_name=snapshot.home_team,
                    away_team_id=snapshot.away_team_id,
                    away_team_name=snapshot.away_team,
                    cache_status=snapshot.cache_status,
                    last_updated_at=snapshot.updated_at,
                    league_country_id=(fixture.get("league") or {}).get("country_id"),
                    league_short_code=(fixture.get("league") or {}).get("short_code"),
                )
                summaries.append(summary)
                results.append(
                    {
                        "fixture_id": snapshot.fixture_id,
                        "cache_status": snapshot.cache_status,
                    }
                )
                if snapshot.cache_status == "partial":
                    partial += 1
                else:
                    warmed += 1
            except Exception as exc:
                failed += 1
                results.append(
                    {
                        "fixture_id": fixture.get("id"),
                        "cache_status": "error",
                        "error": str(exc),
                    }
                )

        self.store.write_fixtures(date, [item.to_dict() for item in summaries])
        return SportmonksWarmupResult(
            date=date,
            leagues=leagues or [],
            fixtures_found=len(fixtures),
            fixtures_warmed=warmed,
            fixtures_partial=partial,
            fixtures_failed=failed,
            output_path=str(self.store.get_date_dir(date)),
            results=results,
        )

    async def get_match(
        self,
        fixture_id: int,
        date: Optional[str] = None,
        refresh_if_stale: bool = True,
    ) -> SportmonksMatchSnapshot:
        payload = self.store.read_match(fixture_id, date)
        if not payload:
            raise FileNotFoundError(f"snapshot not found for fixture_id={fixture_id}")
        if payload.get("cache_status") == "stale" and refresh_if_stale:
            return await self.refresh_match(
                fixture_id=fixture_id,
                date=date,
                layers=None,
            )
        return SportmonksMatchSnapshot(**payload)

    async def refresh_match(
        self,
        fixture_id: int,
        date: Optional[str] = None,
        layers: Optional[list[str]] = None,
    ) -> SportmonksMatchSnapshot:
        if self.collector is None:
            raise RuntimeError("collector is required for refresh_match()")

        if date is None:
            raise ValueError("date is required for refresh_match()")

        existing_snapshot = self.store.read_match(fixture_id, date)
        if not existing_snapshot:
            raise FileNotFoundError(f"snapshot not found for fixture_id={fixture_id}")

        fixture = self.store.read_raw_layer(fixture_id, date, "fixture") or self._snapshot_to_fixture(existing_snapshot)
        raw_layers = await self.collector.collect_match_layers(fixture)

        if layers:
            raw_layers = {
                key: value
                for key, value in raw_layers.items()
                if key == "fixture" or key in set(layers)
            }

        snapshot = build_match_snapshot(raw_layers, existing_snapshot=existing_snapshot)
        self.store.write_match(
            fixture_id=snapshot.fixture_id,
            date=date,
            snapshot=snapshot.to_dict(),
            home_team=snapshot.home_team,
            away_team=snapshot.away_team,
        )
        self.store.write_meta(
            fixture_id=snapshot.fixture_id,
            date=date,
            meta={
                "fixture_id": snapshot.fixture_id,
                "cache_status": snapshot.cache_status,
                "available_layers": list(snapshot.available_layers),
                "missing_layers": list(snapshot.missing_layers),
                "updated_at": snapshot.updated_at,
                "expires_at": snapshot.expires_at,
            },
        )
        for layer, payload in raw_layers.items():
            if payload is not None:
                self.store.write_raw_layer(snapshot.fixture_id, date, layer, payload)
        return snapshot

    async def get_cache_status(
        self,
        date: Optional[str] = None,
        fixture_id: Optional[int] = None,
    ) -> dict[str, Any]:
        if fixture_id is not None:
            meta = self.store.read_meta(fixture_id, date)
            snapshot = self.store.read_match(fixture_id, date)
            return {
                "fixture_id": fixture_id,
                "date": date,
                "cache_status": (meta or {}).get("cache_status") or (snapshot or {}).get("cache_status", "missing"),
                "meta": meta,
            }

        if date is None:
            raise ValueError("date or fixture_id is required")

        fixtures = self.store.read_fixtures(date)
        counts: dict[str, int] = {}
        for fixture in fixtures:
            status = fixture.get("cache_status", "missing")
            counts[status] = counts.get(status, 0) + 1

        return {
            "date": date,
            "total_fixtures": len(fixtures),
            "status_counts": counts,
        }

    @staticmethod
    def _snapshot_to_fixture(snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": snapshot["fixture_id"],
            "starting_at": snapshot["kickoff_time"],
            "league": {"name": snapshot["league"]},
            "season_id": snapshot["season_id"],
            "participants": [
                {
                    "id": snapshot["home_team_id"],
                    "name": snapshot["home_team"],
                    "meta": {"location": "home"},
                },
                {
                    "id": snapshot["away_team_id"],
                    "name": snapshot["away_team"],
                    "meta": {"location": "away"},
                },
            ],
        }
