#!/usr/bin/env python3

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.collectors.footystats import FootyStatsClient
from src.collectors.clubelo import ClubEloClient
from src.collectors.understat import UnderstatClient
from src.collectors.transfermarkt import TransfermarktClient
from src.collectors.odds_api import OddsAPIClient
from src.storage.repository import get_repository
from src.utils.logger import logger
from config.settings import settings


class DataUpdateScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.footystats = FootyStatsClient()
        self.clubelo = ClubEloClient()
        self.understat = UnderstatClient()
        self.transfermarkt = TransfermarktClient()
        self.odds = OddsAPIClient()
        self.repo = get_repository()
        self._last_execution = {}

    def configure_jobs(self):
        self.scheduler.add_job(
            self.update_standings_and_elo,
            CronTrigger(hour=6, minute=0),
            id="update_standings_elo",
            name="Update Standings and Elo",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self.update_team_stats,
            CronTrigger(hour=12, minute=0),
            id="update_team_stats",
            name="Update Team Stats",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self.sync_understat_all,
            CronTrigger(day_of_week="mon", hour=2, minute=0),
            id="sync_understat",
            name="Sync Understat Data",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self.update_injuries,
            CronTrigger(hour="*/6"),
            id="update_injuries",
            name="Update Injury Data",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self.update_odds_snapshot,
            IntervalTrigger(hours=4),
            id="update_odds",
            name="Update Odds Snapshot",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self.health_check,
            IntervalTrigger(hours=1),
            id="health_check",
            name="Health Check",
            replace_existing=True,
        )

        logger.info("Scheduler jobs configured")

    async def update_standings_and_elo(self):
        logger.info("Starting: Update standings and Elo")
        try:
            leagues = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
            
            for league in leagues:
                try:
                    season_id = self._get_season_id(league)
                    if season_id:
                        table = await self.footystats.get_league_table(season_id)
                        if table:
                            logger.info(f"Updated standings for {league}")
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Error updating standings for {league}: {e}")

            self._last_execution["standings_elo"] = datetime.now()
            logger.info("Completed: Update standings and Elo")

        except Exception as e:
            logger.error(f"Job failed: update_standings_and_elo - {e}")

    async def update_team_stats(self):
        logger.info("Starting: Update team stats")
        try:
            teams = self._get_tracked_teams()
            
            for team_id in teams:
                try:
                    stats = await self.footystats.get_team(team_id)
                    if stats:
                        logger.debug(f"Updated stats for team {team_id}")
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.warning(f"Error updating team {team_id}: {e}")

            self._last_execution["team_stats"] = datetime.now()
            logger.info(f"Completed: Update team stats ({len(teams)} teams)")

        except Exception as e:
            logger.error(f"Job failed: update_team_stats - {e}")

    async def sync_understat_all(self):
        logger.info("Starting: Sync Understat data")
        try:
            leagues = ["EPL", "La_liga", "Serie_A", "Bundesliga", "Ligue_1"]
            season = self._get_current_season()

            for league in leagues:
                try:
                    matches = await self.understat.get_league_matches(league, season)
                    if matches:
                        logger.info(f"Synced {len(matches)} matches for {league}")
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.warning(f"Error syncing Understat for {league}: {e}")

            self._last_execution["understat"] = datetime.now()
            logger.info("Completed: Sync Understat data")

        except Exception as e:
            logger.error(f"Job failed: sync_understat_all - {e}")

    async def update_injuries(self):
        logger.info("Starting: Update injury data")
        try:
            teams = self._get_tracked_teams()
            
            for team_name in teams[:20]:
                try:
                    injuries = await self.transfermarkt.get_injuries(team_name)
                    if injuries:
                        logger.debug(f"Updated injuries for {team_name}: {len(injuries)} players")
                    await asyncio.sleep(3)
                except Exception as e:
                    logger.warning(f"Error updating injuries for {team_name}: {e}")

            self._last_execution["injuries"] = datetime.now()
            logger.info("Completed: Update injury data")

        except Exception as e:
            logger.error(f"Job failed: update_injuries - {e}")

    async def update_odds_snapshot(self):
        logger.info("Starting: Update odds snapshot")
        try:
            leagues = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
            
            for league in leagues:
                try:
                    odds = await self.odds.get_odds(league)
                    if odds:
                        logger.debug(f"Updated odds for {league}")
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.warning(f"Error updating odds for {league}: {e}")

            self._last_execution["odds"] = datetime.now()
            logger.info("Completed: Update odds snapshot")

        except Exception as e:
            logger.error(f"Job failed: update_odds_snapshot - {e}")

    async def health_check(self):
        now = datetime.now()
        
        for job_name, last_time in self._last_execution.items():
            if last_time:
                elapsed = (now - last_time).total_seconds() / 3600
                if elapsed > 24:
                    logger.warning(f"Job {job_name} hasn't run in {elapsed:.1f} hours")

    def _get_season_id(self, league: str) -> Optional[str]:
        season_map = {
            "Premier League": "4328",
            "La Liga": "4329",
            "Serie A": "4330",
            "Bundesliga": "4331",
            "Ligue 1": "4332",
        }
        return season_map.get(league)

    def _get_tracked_teams(self) -> List[str]:
        return [
            "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton",
            "Chelsea", "Crystal Palace", "Everton", "Fulham", "Liverpool",
            "Manchester City", "Manchester United", "Newcastle United",
            "Nottingham Forest", "Tottenham Hotspur", "West Ham United",
            "Wolverhampton", "Barcelona", "Real Madrid", "Atletico Madrid",
            "Bayern Munich", "Borussia Dortmund", "AC Milan", "Inter Milan",
            "Juventus", "Napoli", "Paris Saint-Germain", "Marseille", "Lyon",
        ]

    def _get_current_season(self) -> str:
        now = datetime.now()
        if now.month >= 8:
            return str(now.year)
        else:
            return str(now.year - 1)

    def start(self):
        self.configure_jobs()
        self.scheduler.start()
        logger.info("Scheduler started")

    def stop(self):
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")


async def main():
    scheduler = DataUpdateScheduler()
    
    try:
        scheduler.start()
        logger.info("Scheduler running. Press Ctrl+C to stop.")
        
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
