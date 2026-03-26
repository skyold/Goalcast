#!/usr/bin/env python3

import asyncio
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from provider import FootyStatsProvider
from provider.football_data.client import FootballDataProvider
from utils.logger import logger


LEAGUE_SEASONS = {
    "Premier League": "4328",
    "La Liga": "4329",
    "Serie A": "4330",
    "Bundesliga": "4331",
    "Ligue 1": "4332",
    "Champions League": "4335",
    "Europa League": "4336",
    "Europa Conference League": "4337",
}

LEAGUE_PRIORITY = [
    "Premier League",
    "La Liga",
    "Serie A",
    "Bundesliga",
    "Ligue 1",
    "Champions League",
    "Europa League",
]


class UpcomingMatchesFinder:
    def __init__(self):
        self.footystats = FootyStatsProvider()
        self.football_data = FootballDataProvider()

    async def get_matches_for_date(
        self,
        date: datetime,
        leagues: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        date_str = date.strftime("%Y-%m-%d")
        leagues = leagues or LEAGUE_PRIORITY

        all_matches = []

        for league in leagues:
            try:
                matches = await self.football_data.get_matches(league, date_str, date_str)
                if matches:
                    data_list = matches if isinstance(matches, list) else matches.get("matches", [])
                    for match in data_list:
                        match["competition"] = league
                        match["date"] = date_str
                    all_matches.extend(data_list)
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.warning(f"Error fetching matches for {league}: {e}")

        return all_matches

    async def get_upcoming_matches(
        self,
        days: int = 7,
        leagues: Optional[List[str]] = None,
        include_odds: bool = False
    ) -> Dict[str, List[Dict[str, Any]]]:
        result = {}

        for i in range(days):
            date = datetime.now() + timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")

            matches = await self.get_matches_for_date(date, leagues)

            if matches:
                result[date_str] = matches

        return result

    def format_output(
        self,
        matches_by_date: Dict[str, List[Dict[str, Any]]],
        format_type: str = "terminal"
    ) -> str:
        if format_type == "json":
            return json.dumps(matches_by_date, indent=2, ensure_ascii=False)

        lines = []
        lines.append("\n" + "=" * 70)
        lines.append("📅 UPCOMING MATCHES")
        lines.append("=" * 70)

        total_matches = sum(len(m) for m in matches_by_date.values())
        lines.append(f"Total: {total_matches} matches across {len(matches_by_date)} days\n")

        for date_str in sorted(matches_by_date.keys()):
            matches = matches_by_date[date_str]
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            day_name = date_obj.strftime("%A")

            lines.append(f"\n📆 {date_str} ({day_name}) - {len(matches)} matches")
            lines.append("-" * 50)

            by_league = {}
            for match in matches:
                league = match.get("competition", "Unknown")
                if league not in by_league:
                    by_league[league] = []
                by_league[league].append(match)

            for league in LEAGUE_PRIORITY:
                if league in by_league:
                    league_matches = by_league[league]
                    lines.append(f"\n  🏆 {league}")

                    for match in league_matches:
                        home = match.get("home_name", "?")
                        away = match.get("away_name", "?")
                        time_str = match.get("start_time", "")
                        match_id = match.get("match_id", "")

                        odds_str = ""
                        if match.get("odds_home"):
                            odds_str = f"  [Odds: {match['odds_home']:.2f}/{match.get('odds_draw', 0):.2f}/{match.get('odds_away', 0):.2f}]"

                        lines.append(f"    • {home} vs {away} ({time_str}){odds_str}")
                        lines.append(f"      ID: {match_id}")

            for league, league_matches in by_league.items():
                if league not in LEAGUE_PRIORITY:
                    lines.append(f"\n  🏆 {league}")
                    for match in league_matches:
                        home = match.get("home_name", "?")
                        away = match.get("away_name", "?")
                        match_id = match.get("match_id", "")
                        lines.append(f"    • {home} vs {away} - ID: {match_id}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="Get upcoming football matches")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look ahead (default: 7)")
    parser.add_argument("--date", type=str, help="Specific date (YYYY-MM-DD)")
    parser.add_argument("--league", type=str, action="append", help="Filter by league (can specify multiple)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--output", type=str, help="Save to file")
    return parser.parse_args()


async def main():
    args = parse_args()

    finder = UpcomingMatchesFinder()

    print(f"\n🔍 Fetching upcoming matches...")

    if args.date:
        date = datetime.strptime(args.date, "%Y-%m-%d")
        matches = await finder.get_matches_for_date(date, args.league)
        matches_by_date = {args.date: matches}
    else:
        matches_by_date = await finder.get_upcoming_matches(
            days=args.days,
            leagues=args.league
        )

    if not matches_by_date:
        print("❌ No matches found. Check your API configuration.")
        return

    format_type = "json" if args.json else "terminal"
    output = finder.format_output(matches_by_date, format_type)

    print(output)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\n💾 Saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
