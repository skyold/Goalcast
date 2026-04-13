#!/usr/bin/env python3
"""
batch_runner.py — Goalcast 数据预热批处理脚本

无 LLM 参与，仅拉取并缓存比赛数据。
适用于定时任务（cron）和大批量预热场景。

用法：
  python scripts/batch_runner.py --provider sportmonks
  python scripts/batch_runner.py --provider footystats --date 2026-04-12
  python scripts/batch_runner.py --provider sportmonks --league "Premier League"
"""
import sys
import asyncio
import argparse
import datetime
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp_server"))

from utils.logger import logger
from config.settings import settings


async def _load_watchlist(provider: str, league_filter: str | None) -> list[str]:
    """Load league list from config/watchlist.yaml."""
    try:
        import yaml
        wl_path = Path(__file__).resolve().parent.parent / "config" / "watchlist.yaml"
        if not wl_path.exists():
            logger.warning("config/watchlist.yaml not found — fetching all leagues")
            return [None]
        with open(wl_path) as f:
            wl = yaml.safe_load(f)
        leagues = [lg["name"] for lg in wl.get(provider, {}).get("leagues", [])]
        if league_filter:
            leagues = [lg for lg in leagues if league_filter.lower() in lg.lower()]
        return leagues or [None]
    except Exception as exc:
        logger.error(f"Failed to load watchlist: {exc}")
        return [None]


async def run_prefetch(provider: str, date: str, league_filter: str | None) -> dict:
    from provider.footystats.client import FootyStatsProvider
    from provider.sportmonks.client import SportmonksProvider
    from provider.understat.client import UnderstatProvider
    from data_strategy.fusion import DataFusion

    fs = FootyStatsProvider()
    us = UnderstatProvider(use_library=True)
    sm = SportmonksProvider() if provider == "sportmonks" else None

    leagues = await _load_watchlist(provider, league_filter)
    logger.info(f"Prefetching {provider} data for {date} | leagues: {leagues}")

    # Step 1: List all matches
    all_matches: list[dict] = []
    for league in leagues:
        if provider == "sportmonks" and sm:
            raw = await sm.get_fixtures_by_date(date, include="participants;scores;league;season")
        elif provider == "footystats":
            raw = await fs.get_todays_matches(date, timezone=None)
        else:
            continue

        data = raw.get("data", []) if isinstance(raw, dict) else []
        for item in data:
            if not isinstance(item, dict):
                continue
            if provider == "sportmonks":
                lg_name = item.get("league", {}).get("name", "") if isinstance(item.get("league"), dict) else ""
                if league and league.lower() not in lg_name.lower():
                    continue
                participants = item.get("participants", [])
                home = next((p for p in participants if p.get("meta", {}).get("location") == "home"), {})
                away = next((p for p in participants if p.get("meta", {}).get("location") == "away"), {})
                all_matches.append({
                    "home_team": home.get("name", ""),
                    "away_team": away.get("name", ""),
                    "competition": lg_name,
                    "match_id": str(item.get("id", "")),
                    "home_team_id": str(home.get("id", "")),
                    "away_team_id": str(away.get("id", "")),
                    "season_id": str(item.get("season_id", "")),
                })
            else:  # footystats
                comp_name = item.get("competition_name", "")
                if league and league.lower() not in comp_name.lower():
                    continue
                all_matches.append({
                    "home_team": item.get("home_name", ""),
                    "away_team": item.get("away_name", ""),
                    "competition": comp_name,
                    "match_id": str(item.get("id", "")),
                    "home_team_id": str(item.get("homeID", "")),
                    "away_team_id": str(item.get("awayID", "")),
                    "season_id": str(item.get("competition_id", "")),
                })

    logger.info(f"Found {len(all_matches)} matches")

    # Step 2: Warm cache for each match
    async def _warm_one(match: dict) -> bool:
        try:
            fusion = DataFusion(
                data_provider=provider,
                footystats=fs,
                understat=us,
                sportmonks=sm,
            )
            await fusion.build(
                fixture_id=match["match_id"],
                match_id=match["match_id"],
                home_team=match["home_team"],
                home_team_id=match["home_team_id"],
                away_team=match["away_team"],
                away_team_id=match["away_team_id"],
                season_id=match["season_id"],
                league=match["competition"],
                match_date=date,
            )
            return True
        except Exception as exc:
            logger.warning(f"  Failed: {match.get('home_team')} vs {match.get('away_team')}: {exc}")
            return False

    results = await asyncio.gather(*(_warm_one(m) for m in all_matches), return_exceptions=True)
    cached = sum(1 for r in results if r is True)
    errors = len(results) - cached

    # Save match list for agent consumption
    output_dir = Path(__file__).resolve().parent.parent / "data" / "cache"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"today_matches_{provider}.json"
    with open(output_path, "w") as f:
        json.dump({"date": date, "provider": provider, "matches": all_matches}, f, ensure_ascii=False, indent=2)

    summary = {
        "date": date,
        "provider": provider,
        "matches_found": len(all_matches),
        "matches_cached": cached,
        "errors": errors,
        "output": str(output_path),
    }
    logger.info(f"Prefetch complete: {summary}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Goalcast batch data prefetcher")
    parser.add_argument("--provider", choices=["sportmonks", "footystats"], required=True)
    parser.add_argument("--date", default=datetime.date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--league", default=None, help="League name filter")
    args = parser.parse_args()

    result = asyncio.run(run_prefetch(args.provider, args.date, args.league))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
