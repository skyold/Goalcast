import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from provider import (
    FootyStatsProvider,
    FootballDataProvider,
    ClubEloProvider,
    OddsProvider,
    WeatherProvider,
    UnderstatProvider,
    TransfermarktProvider,
)
from datasource import (
    MatchDataSource,
    TeamDataSource,
    StandingsDataSource,
    EloDataSource,
    OddsDataSource,
    WeatherDataSource,
    InjuryDataSource,
    registry,
    Injury,
    InjurySeverity,
    compute_xg_adjustment,
    classify_player_importance,
)
from datasource.types import DataSourceType, Match, Team, Elo, Odds, Weather
from aggregator.schema import (
    AnalysisInput,
    MatchInfo,
    TeamStats,
    OddsData,
    ContextData,
    WeatherData,
    DataQuality,
    MatchType,
    DataQualityLevel,
)
from utils.logger import logger
from config.settings import settings


class MatchBuilder:
    def __init__(
        self,
        footystats_provider: Optional[FootyStatsProvider] = None,
        football_data_provider: Optional[FootballDataProvider] = None,
        clubelo_provider: Optional[ClubEloProvider] = None,
        odds_provider: Optional[OddsProvider] = None,
        weather_provider: Optional[WeatherProvider] = None,
        understat_provider: Optional[UnderstatProvider] = None,
        transfermarkt_provider: Optional[TransfermarktProvider] = None,
    ):
        self.footystats = footystats_provider or FootyStatsProvider()
        self.football_data = football_data_provider or FootballDataProvider()
        self.clubelo = clubelo_provider or ClubEloProvider()
        self.odds = odds_provider or OddsProvider()
        self.weather = weather_provider or WeatherProvider()
        self.understat = understat_provider or UnderstatProvider()
        self.transfermarkt = transfermarkt_provider or TransfermarktProvider()
        
        self._setup_datasources()

    def _setup_datasources(self):
        self.match_ds = MatchDataSource(providers=[self.footystats, self.football_data])
        self.team_ds = TeamDataSource(providers=[self.footystats, self.understat, self.clubelo])
        self.standings_ds = StandingsDataSource(providers=[self.footystats, self.football_data])
        self.elo_ds = EloDataSource(providers=[self.clubelo])
        self.odds_ds = OddsDataSource(providers=[self.odds])
        self.weather_ds = WeatherDataSource(providers=[self.weather])
        self.injury_ds = InjuryDataSource(providers=[self.transfermarkt])
        
        registry.register(self.match_ds)
        registry.register(self.team_ds)
        registry.register(self.standings_ds)
        registry.register(self.elo_ds)
        registry.register(self.odds_ds)
        registry.register(self.weather_ds)
        registry.register(self.injury_ds)

    async def build(
        self, match_id: str, manual_overrides: Optional[Dict[str, Any]] = None
    ) -> Optional[AnalysisInput]:
        logger.info(f"Building analysis input for match_id={match_id}")
        manual_overrides = manual_overrides or {}

        match_data = await self.footystats.get_match(match_id)
        if not match_data:
            logger.error(f"Match not found: {match_id}")
            return None

        home_id = match_data.get("home_id")
        away_id = match_data.get("away_id")
        home_team = match_data.get("home_name", "")
        away_team = match_data.get("away_name", "")
        competition = match_data.get("competition", "")

        home_stats_data, away_stats_data = await self._fetch_team_stats(home_id, away_id)

        home_elo, away_elo = await asyncio.gather(
            self.clubelo.get_elo(home_team),
            self.clubelo.get_elo(away_team),
        )

        odds_data = await self._fetch_odds(competition, match_id)

        league_table = await self._fetch_league_table(match_data)
        home_position, away_position = self._extract_positions(league_table, home_id, away_id)

        weather_coords = self.weather.get_stadium_coordinates(home_team)
        weather_data = None
        if weather_coords:
            match_dt = datetime.now()
            raw_weather = await self.weather.get_weather(
                weather_coords["lat"], weather_coords["lon"]
            )
            if raw_weather:
                weather_data = self.weather.parse_weather_data(raw_weather)

        understat_home, understat_away = await self._fetch_understat_data(
            home_team, away_team, competition
        )

        injuries_home, injuries_away = await self._fetch_injury_data(home_team, away_team)

        data_quality = self._assess_data_quality(
            match_data, home_stats_data, away_stats_data, odds_data, understat_home, understat_away
        )

        home_stats = self._build_team_stats(
            home_stats_data, home_elo, home_position, understat_home, injuries_home
        )
        away_stats = self._build_team_stats(
            away_stats_data, away_elo, away_position, understat_away, injuries_away
        )

        if "lineup_home" in manual_overrides:
            home_stats.injuries = manual_overrides.get("lineup_home", [])
        if "lineup_away" in manual_overrides:
            away_stats.injuries = manual_overrides.get("lineup_away", [])
        if "injuries_home" in manual_overrides:
            home_stats.injuries = manual_overrides["injuries_home"]
        if "injuries_away" in manual_overrides:
            away_stats.injuries = manual_overrides["injuries_away"]

        match_type = self._classify_match_type(match_data)

        match_info = MatchInfo(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            match_type=match_type,
            missing_data=data_quality.missing_fields,
            data_quality=data_quality.quality_level,
        )

        xg_adj_home = compute_xg_adjustment(injuries_home) if injuries_home else 0.0
        xg_adj_away = compute_xg_adjustment(injuries_away) if injuries_away else 0.0

        context = ContextData(
            injuries_home=[i.player_name for i in injuries_home] if injuries_home else [],
            injuries_away=[i.player_name for i in injuries_away] if injuries_away else [],
            motivation_notes=self._compute_motivation_notes(match_data, home_position, away_position),
        )

        weather = None
        if weather_data:
            weather = WeatherData(**weather_data)

        return AnalysisInput(
            match_info=match_info,
            home_stats=home_stats,
            away_stats=away_stats,
            odds=odds_data,
            context=context,
            weather=weather,
            data_quality=data_quality,
        )

    async def build_from_team_names(
        self,
        home_team: str,
        away_team: str,
        competition: str = "",
        manual_overrides: Optional[Dict[str, Any]] = None,
    ) -> Optional[AnalysisInput]:
        logger.info(f"Building analysis input for {home_team} vs {away_team}")
        manual_overrides = manual_overrides or {}

        home_stats_data, away_stats_data = await self._fetch_team_stats_by_name(
            home_team, away_team, competition
        )

        home_elo, away_elo = await asyncio.gather(
            self.clubelo.get_elo(home_team),
            self.clubelo.get_elo(away_team),
        )

        odds_data = await self._fetch_odds_by_teams(home_team, away_team, competition)

        understat_home, understat_away = await self._fetch_understat_data(
            home_team, away_team, competition
        )

        injuries_home, injuries_away = await self._fetch_injury_data(home_team, away_team)

        weather_coords = self.weather.get_stadium_coordinates(home_team)
        weather_data = None
        if weather_coords:
            raw_weather = await self.weather.get_weather(
                weather_coords["lat"], weather_coords["lon"]
            )
            if raw_weather:
                weather_data = self.weather.parse_weather_data(raw_weather)

        data_quality = self._assess_data_quality(
            {"home_name": home_team, "away_name": away_team, "competition": competition},
            home_stats_data or {},
            away_stats_data or {},
            odds_data,
            understat_home,
            understat_away,
        )

        home_stats = self._build_team_stats(
            home_stats_data or {}, home_elo, None, understat_home, injuries_home
        )
        away_stats = self._build_team_stats(
            away_stats_data or {}, away_elo, None, understat_away, injuries_away
        )

        if "injuries_home" in manual_overrides:
            home_stats.injuries = manual_overrides["injuries_home"]
        if "injuries_away" in manual_overrides:
            away_stats.injuries = manual_overrides["injuries_away"]

        match_info = MatchInfo(
            match_id=f"manual_{home_team}_{away_team}",
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            match_type=self._classify_match_type({"competition": competition}),
            missing_data=data_quality.missing_fields,
            data_quality=data_quality.quality_level,
        )

        context = ContextData(
            injuries_home=[i.player_name for i in injuries_home] if injuries_home else [],
            injuries_away=[i.player_name for i in injuries_away] if injuries_away else [],
            motivation_notes=None,
        )

        weather = None
        if weather_data:
            weather = WeatherData(**weather_data)

        return AnalysisInput(
            match_info=match_info,
            home_stats=home_stats,
            away_stats=away_stats,
            odds=odds_data,
            context=context,
            weather=weather,
            data_quality=data_quality,
        )

    async def _fetch_team_stats(
        self, home_id: Optional[str], away_id: Optional[str]
    ) -> tuple:
        tasks = []
        if home_id:
            tasks.append(self.footystats.get_team(home_id))
        if away_id:
            tasks.append(self.footystats.get_team(away_id))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        home_data = results[0] if home_id and len(results) > 0 else {}
        away_data = results[1] if away_id and len(results) > 1 else {}

        if isinstance(home_data, Exception):
            logger.warning(f"Error fetching home team stats: {home_data}")
            home_data = {}
        if isinstance(away_data, Exception):
            logger.warning(f"Error fetching away team stats: {away_data}")
            away_data = {}

        return home_data, away_data

    async def _fetch_team_stats_by_name(
        self, home_team: str, away_team: str, competition: str
    ) -> tuple:
        try:
            if hasattr(self.footystats, 'get_team_by_name'):
                home_data, away_data = await asyncio.gather(
                    self.footystats.get_team_by_name(home_team),
                    self.footystats.get_team_by_name(away_team),
                    return_exceptions=True,
                )

                if isinstance(home_data, Exception):
                    logger.warning(f"Error fetching home team stats: {home_data}")
                    home_data = None
                if isinstance(away_data, Exception):
                    logger.warning(f"Error fetching away team stats: {away_data}")
                    away_data = None

                return home_data, away_data
            else:
                logger.warning("get_team_by_name not available in FootyStatsProvider")
                return None, None

        except Exception as e:
            logger.warning(f"Error fetching team stats by name: {e}")
            return None, None

    async def _fetch_understat_data(
        self, home_team: str, away_team: str, competition: str
    ) -> tuple:
        try:
            season = self._get_current_season()
            
            home_matches, away_matches = await asyncio.gather(
                self.understat.get_team_matches(home_team, competition, season),
                self.understat.get_team_matches(away_team, competition, season),
                return_exceptions=True,
            )

            home_data = None
            away_data = None

            if not isinstance(home_matches, Exception) and home_matches:
                home_data = {
                    "recent_form": self._compute_recent_form(home_matches, home_team, 5),
                    "matches": home_matches,
                }

            if not isinstance(away_matches, Exception) and away_matches:
                away_data = {
                    "recent_form": self._compute_recent_form(away_matches, away_team, 5),
                    "matches": away_matches,
                }

            return home_data, away_data

        except Exception as e:
            logger.warning(f"Error fetching Understat data: {e}")
            return None, None

    def _compute_recent_form(
        self, matches: List[Dict[str, Any]], team_name: str, n: int = 5
    ) -> Dict[str, Any]:
        form = []
        total_xg = 0.0
        total_xga = 0.0
        count = 0

        for match in matches[:n]:
            is_home = match.get("home_team", "").lower() == team_name.lower()
            
            if is_home:
                team_goals = match.get("home_goals", 0)
                opp_goals = match.get("away_goals", 0)
                xg = match.get("home_xg", 0) or 0
                xga = match.get("away_xg", 0) or 0
            else:
                team_goals = match.get("away_goals", 0)
                opp_goals = match.get("home_goals", 0)
                xg = match.get("away_xg", 0) or 0
                xga = match.get("home_xg", 0) or 0

            if team_goals > opp_goals:
                form.append("W")
            elif team_goals < opp_goals:
                form.append("L")
            else:
                form.append("D")

            total_xg += xg
            total_xga += xga
            count += 1

        return {
            "form": form,
            "xg_avg": total_xg / count if count > 0 else 0,
            "xga_avg": total_xga / count if count > 0 else 0,
        }

    async def _fetch_injury_data(
        self, home_team: str, away_team: str
    ) -> tuple:
        try:
            home_injuries, away_injuries = await asyncio.gather(
                self.transfermarkt.get_injuries(home_team),
                self.transfermarkt.get_injuries(away_team),
                return_exceptions=True,
            )

            home_list = []
            away_list = []

            if not isinstance(home_injuries, Exception) and home_injuries:
                home_list = classify_player_importance(home_injuries)

            if not isinstance(away_injuries, Exception) and away_injuries:
                away_list = classify_player_importance(away_injuries)

            return home_list, away_list

        except Exception as e:
            logger.warning(f"Error fetching injury data: {e}")
            return [], []

    async def _fetch_odds(
        self, competition: str, match_id: str
    ) -> Optional[OddsData]:
        try:
            odds_result = await self.odds.get_odds(competition, match_id)
            if not odds_result or not odds_result.get("data"):
                return None

            odds_list = odds_result["data"]
            if not odds_list:
                return None

            bookmaker_data = odds_list[0]
            markets = bookmaker_data.get("markets", [])
            if not markets:
                return None

            h2h_market = markets[0]
            outcomes = h2h_market.get("outcomes", [])

            odds_dict = {o["name"].lower(): o["price"] for o in outcomes}

            return OddsData(
                opening_home=odds_dict.get("home"),
                opening_draw=odds_dict.get("draw"),
                opening_away=odds_dict.get("away"),
                current_home=odds_dict.get("home"),
                current_draw=odds_dict.get("draw"),
                current_away=odds_dict.get("away"),
            )

        except Exception as e:
            logger.warning(f"Error fetching odds: {e}")
            return None

    async def _fetch_odds_by_teams(
        self, home_team: str, away_team: str, competition: str
    ) -> Optional[OddsData]:
        try:
            if hasattr(self.odds, 'get_odds_by_teams'):
                odds_result = await self.odds.get_odds_by_teams(home_team, away_team, competition)
                if not odds_result:
                    return None

                odds_dict = odds_result

                return OddsData(
                    opening_home=odds_dict.get("opening_home") or odds_dict.get("home"),
                    opening_draw=odds_dict.get("opening_draw") or odds_dict.get("draw"),
                    opening_away=odds_dict.get("opening_away") or odds_dict.get("away"),
                    current_home=odds_dict.get("current_home") or odds_dict.get("home"),
                    current_draw=odds_dict.get("current_draw") or odds_dict.get("draw"),
                    current_away=odds_dict.get("current_away") or odds_dict.get("away"),
                )
            else:
                logger.warning("get_odds_by_teams not available in OddsProvider")
                return None

        except Exception as e:
            logger.warning(f"Error fetching odds by teams: {e}")
            return None

    async def _fetch_league_table(self, match_data: Dict[str, Any]) -> Optional[list]:
        season_id = match_data.get("season_id")
        if not season_id:
            return None

        try:
            table = await self.footystats.get_league_table(season_id)
            return table
        except Exception as e:
            logger.warning(f"Error fetching league table: {e}")
            return None

    def _extract_positions(
        self, table: Optional[list], home_id: Optional[str], away_id: Optional[str]
    ) -> tuple:
        if not table:
            return None, None

        home_pos = None
        away_pos = None

        for entry in table:
            if entry.get("team_id") == home_id:
                home_pos = entry.get("position")
            if entry.get("team_id") == away_id:
                away_pos = entry.get("position")

        return home_pos, away_pos

    def _build_team_stats(
        self,
        data: Dict[str, Any],
        elo: Optional[float],
        position: Optional[int],
        understat_data: Optional[Dict[str, Any]] = None,
        injuries: Optional[List[Injury]] = None,
    ) -> TeamStats:
        recent_form = data.get("recent_form", [])
        xg_avg = None
        xga_avg = None

        if understat_data and understat_data.get("recent_form"):
            form_data = understat_data["recent_form"]
            recent_form = form_data.get("form", [])
            xg_avg = form_data.get("xg_avg")
            xga_avg = form_data.get("xga_avg")

        injury_names = []
        if injuries:
            injury_names = [i.player_name for i in injuries if i.severity in [InjurySeverity.LONG_TERM, InjurySeverity.MEDIUM_TERM]]

        return TeamStats(
            team_id=data.get("team_id"),
            team_name=data.get("team_name"),
            xg_home=data.get("season_xg_home"),
            xg_away=data.get("season_xg_away"),
            xga_home=data.get("season_xga_home"),
            xga_away=data.get("season_xga_away"),
            ppg=data.get("ppg_overall"),
            possession_home=data.get("season_possession_home"),
            possession_away=data.get("season_possession_away"),
            recent_form=recent_form,
            elo=elo,
            league_position=position,
            injuries=injury_names,
        )

    def _assess_data_quality(
        self,
        match_data: Dict[str, Any],
        home_stats: Dict[str, Any],
        away_stats: Dict[str, Any],
        odds_data: Optional[OddsData],
        understat_home: Optional[Dict[str, Any]] = None,
        understat_away: Optional[Dict[str, Any]] = None,
    ) -> DataQuality:
        missing = []
        penalty = 0

        if not home_stats.get("season_xg_home"):
            missing.append("home_xg")
            penalty += 5

        if not away_stats.get("season_xg_away"):
            missing.append("away_xg")
            penalty += 5

        if not odds_data or not odds_data.current_home:
            missing.append("odds")
            penalty += 5

        if not home_stats.get("recent_form") and not (understat_home and understat_home.get("recent_form")):
            missing.append("home_recent_form")
            penalty += 3

        if not away_stats.get("recent_form") and not (understat_away and understat_away.get("recent_form")):
            missing.append("away_recent_form")
            penalty += 3

        if not understat_home:
            missing.append("understat_home")
            penalty += 2

        if not understat_away:
            missing.append("understat_away")
            penalty += 2

        if penalty >= 15:
            quality = DataQualityLevel.LOW
        elif penalty >= 8:
            quality = DataQualityLevel.MEDIUM
        else:
            quality = DataQualityLevel.HIGH

        return DataQuality(
            missing_fields=missing,
            quality_level=quality,
            confidence_penalty=min(penalty, 20),
        )

    def _classify_match_type(self, match_data: Dict[str, Any]) -> MatchType:
        competition = match_data.get("competition", "")
        status = match_data.get("status", "")

        if "cup" in competition.lower() or "league cup" in competition.lower():
            return MatchType.B

        if "champions" in competition.lower() or "europa" in competition.lower():
            if "Second Leg" in match_data.get("stage", ""):
                return MatchType.C

        return MatchType.A

    def _get_current_season(self) -> str:
        now = datetime.now()
        if now.month >= 8:
            return str(now.year)
        else:
            return str(now.year - 1)

    def _compute_motivation_notes(
        self,
        match_data: Dict[str, Any],
        home_position: Optional[int],
        away_position: Optional[int],
    ) -> Optional[str]:
        notes = []
        competition = match_data.get("competition", "")

        if home_position and away_position:
            if home_position <= 4 and away_position <= 4:
                notes.append("Top 4 clash - high motivation for both sides")
            elif home_position >= 18 and away_position >= 18:
                notes.append("Relegation battle - high motivation for both sides")
            elif home_position and home_position <= 6 and away_position and away_position >= 15:
                notes.append("Potential motivation gap - home side chasing European spots")
            elif home_position and home_position >= 15 and away_position and away_position <= 6:
                notes.append("Potential motivation gap - away side chasing European spots")

        if "champions" in competition.lower():
            notes.append("Champions League match - elevated motivation")

        return "; ".join(notes) if notes else None
