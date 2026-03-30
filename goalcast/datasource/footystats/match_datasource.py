from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from goalcast.provider.footystats.client import FootyStatsProvider
from goalcast.domain.entities.match_basic import MatchBasicData
from goalcast.domain.entities.match_stats import MatchStatsData
from goalcast.domain.entities.match_advanced import MatchAdvancedData, LineupPlayer
from goalcast.domain.entities.match_odds import MatchOddsData
from goalcast.domain.entities.match_teams import MatchTeamsData, TeamForm, TeamSeasonStats
from goalcast.domain.entities.match_others import MatchOthersData
from goalcast.domain.entities.full_match_data import FullMatchData
from goalcast.utils.logger import logger


class MatchDataDataSource:
    """
    比赛数据源

    设计理念:
    1. 按数据类别组织数据获取
    2. 只获取用户需要的数据
    3. 计算衍生数据（如球队状态）
    4. 为未来 ML 预留接口
    """

    def __init__(self, provider: FootyStatsProvider, debug: bool = False):
        self.provider = provider
        self.debug = debug
        self._raw_data: Dict[str, Any] = {}
        self._match_details_cache: Optional[Dict[str, Any]] = None
        self._last_match_id: Optional[int] = None

    def get_raw_data(self, category: str) -> Optional[Dict[str, Any]]:
        """获取原始 API 数据"""
        return self._raw_data.get(category)

    def clear_raw_data(self):
        """清除原始数据"""
        self._raw_data.clear()

    async def _get_match_details_cached(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        获取比赛详情（带缓存，避免重复API调用）

        同一 match_id 多次调用只请求一次 API

        Returns:
            API 响应数据或 None
        """
        if self._last_match_id != match_id or self._match_details_cache is None:
            self._last_match_id = match_id
            self._match_details_cache = await self.provider.get_match_details(match_id)
        return self._match_details_cache

    async def get_match_basic(self, match_id: int) -> Optional[MatchBasicData]:
        """
        获取比赛基础数据

        调用策略:
        1. 先从缓存获取（同一 match_id 多次调用不重复请求）
        2. 调用 Match Details API

        Returns:
            MatchBasicData 或 None
        """
        logger.debug(f"Datasource: get_match_basic(match_id={match_id})")

        result = await self._get_match_details_cached(match_id)

        if not result or not result.get('success'):
            logger.error(f"Failed to get match details for {match_id}")
            return None

        data = result.get('data', {})
        if self.debug:
            self._raw_data['basic'] = data

        return self._parse_basic_data(data)

    async def get_match_stats(self, match_id: int) -> Optional[MatchStatsData]:
        """
        获取比赛统计数据

        来源：Match Details API（包含完整统计）

        Returns:
            MatchStatsData 或 None
        """
        logger.debug(f"Datasource: get_match_stats(match_id={match_id})")

        result = await self._get_match_details_cached(match_id)
        if not result or not result.get('success'):
            return None

        data = result.get('data', {})
        if self.debug:
            self._raw_data['stats'] = data
        return self._parse_stats_data(data)

    async def get_match_advanced(self, match_id: int) -> Optional[MatchAdvancedData]:
        """
        获取高级分析数据

        来源：Match Details API

        Returns:
            MatchAdvancedData 或 None
        """
        logger.debug(f"Datasource: get_match_advanced(match_id={match_id})")

        result = await self._get_match_details_cached(match_id)
        if not result or not result.get('success'):
            return None

        data = result.get('data', {})
        if self.debug:
            self._raw_data['advanced'] = data
        return self._parse_advanced_data(data)

    async def get_match_odds(self, match_id: int) -> Optional[MatchOddsData]:
        """
        获取赔率数据

        来源：Match Details API（包含完整赔率对比）

        Returns:
            MatchOddsData 或 None
        """
        logger.debug(f"Datasource: get_match_odds(match_id={match_id})")

        result = await self._get_match_details_cached(match_id)
        if not result or not result.get('success'):
            return None

        data = result.get('data', {})
        if self.debug:
            self._raw_data['odds'] = data
        odds_data = self._parse_odds_data(data)

        if odds_data:
            odds_data.calculate_implied_probabilities()

        return odds_data

    async def get_match_teams(self, match_id: int) -> Optional[MatchTeamsData]:
        """
        获取球队数据

        来源：
        - Team API: 球队详情
        - LastX API: 球队近况
        - League Teams API: 赛季统计

        Returns:
            MatchTeamsData 或 None
        """
        logger.debug(f"Datasource: get_match_teams(match_id={match_id})")

        basic_data = await self.get_match_basic(match_id)
        if not basic_data:
            return None

        home_team_id = basic_data.home_team_id
        away_team_id = basic_data.away_team_id
        season_id = basic_data.season_id

        home_form = await self._get_team_form(home_team_id)
        away_form = await self._get_team_form(away_team_id)

        home_season_stats = await self._get_team_season_stats(home_team_id, season_id)
        away_season_stats = await self._get_team_season_stats(away_team_id, season_id)

        h2h_data = await self._get_h2h_data(match_id)

        teams_data = MatchTeamsData(
            match_id=match_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_form=home_form,
            away_form=away_form,
            home_season_stats=home_season_stats,
            away_season_stats=away_season_stats,
        )

        if h2h_data:
            teams_data.h2h_total = h2h_data.get('total_matches', 0)
            teams_data.h2h_home_wins = h2h_data.get('home_wins', 0)
            teams_data.h2h_away_wins = h2h_data.get('away_wins', 0)
            teams_data.h2h_draws = h2h_data.get('draws', 0)
            teams_data.h2h_avg_goals = h2h_data.get('avg_goals', 0.0)
            teams_data.h2h_btts_percentage = h2h_data.get('btts_pct', 0.0)
            teams_data.h2h_over_25_count = h2h_data.get('over_25_count', 0)
            teams_data.h2h_btts_count = h2h_data.get('btts_count', 0)
            teams_data.h2h_over_25_percentage = h2h_data.get('over_25_pct', 0.0)
            teams_data.h2h_total_goals = h2h_data.get('total_goals', 0)

        return teams_data

    async def get_match_others(self, match_id: int) -> Optional[MatchOthersData]:
        """
        获取其他补充数据

        来源：Various APIs

        Returns:
            MatchOthersData 或 None
        """
        logger.debug(f"Datasource: get_match_others(match_id={match_id})")

        basic_data = await self.get_match_basic(match_id)
        if not basic_data:
            return None

        season_id = basic_data.season_id

        others_data = MatchOthersData(match_id=match_id)

        return others_data

    async def get_full_match_data(self, match_id: int) -> Optional[FullMatchData]:
        """
        获取完整比赛数据（聚合所有类别）

        Returns:
            FullMatchData 或 None
        """
        logger.debug(f"Datasource: get_full_match_data(match_id={match_id})")

        full_data = FullMatchData(match_id=match_id)

        full_data.basic = await self.get_match_basic(match_id)
        if not full_data.basic:
            return None

        full_data.stats = await self.get_match_stats(match_id)
        full_data.advanced = await self.get_match_advanced(match_id)
        full_data.odds = await self.get_match_odds(match_id)
        full_data.teams = await self.get_match_teams(match_id)
        full_data.others = await self.get_match_others(match_id)

        return full_data

    def _parse_basic_data(self, data: dict) -> MatchBasicData:
        """解析基础数据"""
        match_time = None
        if data.get('date_unix'):
            match_time = datetime.fromtimestamp(data['date_unix'])

        half_time = data.get('half_time', {})
        if isinstance(half_time, dict):
            half_time_home = half_time.get('team_a', 0)
            half_time_away = half_time.get('team_b', 0)
        else:
            half_time_home = 0
            half_time_away = 0

        return MatchBasicData(
            match_id=data.get('id', 0),
            season_id=data.get('competition_id', 0),
            competition_name=None,
            home_team_id=data.get('homeID', 0),
            away_team_id=data.get('awayID', 0),
            home_team_name=data.get('home_name'),
            away_team_name=data.get('away_name'),
            match_time=match_time,
            date_unix=data.get('date_unix'),
            status=data.get('status', 'incomplete'),
            home_score=data.get('homeGoalCount', 0),
            away_score=data.get('awayGoalCount', 0),
            half_time_home=half_time_home,
            half_time_away=half_time_away,
            game_week=data.get('game_week'),
            round_id=data.get('roundID'),
            venue=data.get('stadium_name'),
        )

    def _parse_stats_data(self, data: dict) -> MatchStatsData:
        """解析统计数据"""
        return MatchStatsData(
            match_id=data.get('id', 0),
            home_shots_on_target=data.get('team_a_shotsOnTarget', -1),
            away_shots_on_target=data.get('team_b_shotsOnTarget', -1),
            home_shots_off_target=data.get('team_a_shotsOffTarget', -1),
            away_shots_off_target=data.get('team_b_shotsOffTarget', -1),
            home_total_shots=data.get('team_a_shots', -1),
            away_total_shots=data.get('team_b_shots', -1),
            home_possession=data.get('team_a_possession', -1),
            away_possession=data.get('team_b_possession', -1),
            home_corners=data.get('team_a_corners', -1),
            away_corners=data.get('team_b_corners', -1),
            total_corners=data.get('totalCornerCount', 0),
            home_offsides=data.get('team_a_offsides', -1),
            away_offsides=data.get('team_b_offsides', -1),
            home_fouls=data.get('team_a_fouls', -1),
            away_fouls=data.get('team_b_fouls', -1),
            home_yellow_cards=data.get('team_a_yellow_cards', 0),
            away_yellow_cards=data.get('team_b_yellow_cards', 0),
            home_red_cards=data.get('team_a_red_cards', 0),
            away_red_cards=data.get('team_b_red_cards', 0),
            btts=data.get('btts', False),
            over_15=data.get('over15', False),
            over_25=data.get('over25', False),
            over_35=data.get('over35', False),
            winning_team_id=data.get('winningTeam'),
        )

    def _parse_advanced_data(self, data: dict) -> MatchAdvancedData:
        """解析高级数据"""
        advanced = MatchAdvancedData(
            match_id=data.get('id', 0),
            home_xg=data.get('team_a_xg'),
            away_xg=data.get('team_b_xg'),
            total_xg=data.get('total_xg'),
            home_xg_prematch=data.get('team_a_xg_prematch'),
            away_xg_prematch=data.get('team_b_xg_prematch'),
            total_xg_prematch=data.get('total_xg_prematch'),
            home_attacks=data.get('team_a_attacks'),
            away_attacks=data.get('team_b_attacks'),
            home_dangerous_attacks=data.get('team_a_dangerous_attacks'),
            away_dangerous_attacks=data.get('team_b_dangerous_attacks'),
            referee_id=data.get('refereeID'),
            weather=data.get('weather'),
            btts_potential=data.get('btts_potential'),
            btts_fhg_potential=data.get('btts_fhg_potential'),
            btts_2hg_potential=data.get('btts_2hg_potential'),
            o25_potential=data.get('o25_potential'),
            o35_potential=data.get('o35_potential'),
            o45_potential=data.get('o45_potential'),
            u25_potential=data.get('u25_potential'),
            u35_potential=data.get('u35_potential'),
            corners_potential=data.get('corners_potential'),
            avg_potential=data.get('avg_potential'),
            pre_match_home_ppg=data.get('pre_match_home_ppg'),
            pre_match_away_ppg=data.get('pre_match_away_ppg'),
            pre_match_teamA_overall_ppg=data.get('pre_match_teamA_overall_ppg'),
            pre_match_teamB_overall_ppg=data.get('pre_match_teamB_overall_ppg'),
            home_ppg=data.get('home_ppg'),
            away_ppg=data.get('away_ppg'),
            matches_completed_minimum=data.get('matches_completed_minimum'),
            game_week=data.get('game_week'),
        )

        lineups_data = data.get('lineups', {})
        if lineups_data:
            advanced.home_lineup = [
                LineupPlayer(
                    player_id=p.get('player_id'),
                    shirt_number=p.get('shirt_number'),
                    events=p.get('player_events', [])
                )
                for p in lineups_data.get('team_a', [])
            ]
            advanced.away_lineup = [
                LineupPlayer(
                    player_id=p.get('player_id'),
                    shirt_number=p.get('shirt_number'),
                    events=p.get('player_events', [])
                )
                for p in lineups_data.get('team_b', [])
            ]

        h2h_data = data.get('h2h', {})
        if h2h_data:
            advanced.h2h_summary = h2h_data
            advanced.h2h_betting_stats = h2h_data.get('betting_stats')
            prev_matches = h2h_data.get('previous_matches_ids', [])
            advanced.h2h_previous_matches = [
                {
                    'id': m.get('id'),
                    'date_unix': m.get('date_unix'),
                    'team_a_goals': m.get('team_a_goals'),
                    'team_b_goals': m.get('team_b_goals'),
                }
                for m in prev_matches
            ]

        trends = data.get('trends') or {}
        advanced.home_trends = [t[1] for t in trends.get('home', []) if len(t) > 1]
        advanced.away_trends = [t[1] for t in trends.get('away', []) if len(t) > 1]

        advanced.home_goals_timings = data.get('homeGoals_timings', [])
        advanced.away_goals_timings = data.get('awayGoals_timings', [])

        return advanced

    def _parse_odds_data(self, data: dict) -> MatchOddsData:
        """解析赔率数据"""
        odds = MatchOddsData(
            match_id=data.get('id', 0),
            odds_home=data.get('odds_ft_1'),
            odds_draw=data.get('odds_ft_x'),
            odds_away=data.get('odds_ft_2'),
            over_25_odds=data.get('odds_ft_over25'),
            under_25_odds=data.get('odds_ft_under25'),
            over_35_odds=data.get('odds_ft_over35'),
            under_35_odds=data.get('odds_ft_under35'),
            btts_yes_odds=data.get('odds_btts_yes'),
            btts_no_odds=data.get('odds_btts_no'),
            odds_doublechance_1x=data.get('odds_doublechance_1x'),
            odds_doublechance_x2=data.get('odds_doublechance_x2'),
            odds_doublechance_12=data.get('odds_doublechance_12'),
            odds_1st_half_result_1=data.get('odds_1st_half_result_1'),
            odds_1st_half_result_x=data.get('odds_1st_half_result_x'),
            odds_1st_half_result_2=data.get('odds_1st_half_result_2'),
            odds_2nd_half_result_1=data.get('odds_2nd_half_result_1'),
            odds_2nd_half_result_x=data.get('odds_2nd_half_result_x'),
            odds_2nd_half_result_2=data.get('odds_2nd_half_result_2'),
            odds_win_to_nil_1=data.get('odds_win_to_nil_1'),
            odds_win_to_nil_2=data.get('odds_win_to_nil_2'),
            odds_team_a_cs_yes=data.get('odds_team_a_cs_yes'),
            odds_team_a_cs_no=data.get('odds_team_a_cs_no'),
            odds_team_b_cs_yes=data.get('odds_team_b_cs_yes'),
            odds_team_b_cs_no=data.get('odds_team_b_cs_no'),
            odds_corners_over_75=data.get('odds_corners_over_75'),
            odds_corners_over_85=data.get('odds_corners_over_85'),
            odds_corners_over_95=data.get('odds_corners_over_95'),
            odds_corners_over_105=data.get('odds_corners_over_105'),
            odds_corners_over_115=data.get('odds_corners_over_115'),
            odds_corners_under_75=data.get('odds_corners_under_75'),
            odds_corners_under_85=data.get('odds_corners_under_85'),
            odds_corners_under_95=data.get('odds_corners_under_95'),
            odds_corners_1=data.get('odds_corners_1'),
            odds_corners_x=data.get('odds_corners_x'),
            odds_corners_2=data.get('odds_corners_2'),
            odds_1st_half_over05=data.get('odds_1st_half_over05'),
            odds_1st_half_over15=data.get('odds_1st_half_over15'),
            odds_1st_half_over25=data.get('odds_1st_half_over25'),
            odds_1st_half_under05=data.get('odds_1st_half_under05'),
            odds_1st_half_under15=data.get('odds_1st_half_under15'),
            odds_1st_half_under25=data.get('odds_1st_half_under25'),
            odds_2nd_half_over05=data.get('odds_2nd_half_over05'),
            odds_2nd_half_over15=data.get('odds_2nd_half_over15'),
            odds_2nd_half_over25=data.get('odds_2nd_half_over25'),
            odds_2nd_half_under05=data.get('odds_2nd_half_under05'),
            odds_2nd_half_under15=data.get('odds_2nd_half_under15'),
            odds_2nd_half_under25=data.get('odds_2nd_half_under25'),
            odds_comparison=data.get('odds_comparison'),
        )

        if odds.odds_comparison:
            odds.extract_pinnacle_odds(odds.odds_comparison)

        return odds

    async def _get_team_form(self, team_id: int) -> Optional[TeamForm]:
        """获取球队状态（从 LastX API）"""
        try:
            result = await self.provider.get_team_last_x_stats(team_id)
            if not result or not result.get('success'):
                return None

            return TeamForm(team_id=team_id)
        except Exception as e:
            logger.error(f"Failed to get team form for {team_id}: {e}")
            return None

    async def _get_team_season_stats(self, team_id: int, season_id: int) -> Optional[TeamSeasonStats]:
        """获取球队赛季统计（从 Team API）"""
        try:
            result = await self.provider.get_team(team_id)
            if not result or not result.get('success'):
                return None

            data = result.get('data', [])
            if not data:
                return None

            team_data = None
            if isinstance(data, list):
                for item in data:
                    if item.get('id') == team_id:
                        team_data = item
                        break
                if team_data is None and len(data) > 0:
                    team_data = data[0]
            else:
                team_data = data

            if not team_data:
                return None

            stats = team_data.get('stats', {})

            def safe_float(val, default=0.0):
                try:
                    return float(val) if val is not None else default
                except (ValueError, TypeError):
                    return default

            def safe_int(val, default=0):
                try:
                    return int(val) if val is not None else default
                except (ValueError, TypeError):
                    return default

            return TeamSeasonStats(
                team_id=team_id,
                season_id=season_id,
                matches_played=team_data.get('matches_played', 0) or stats.get('seasonMatchesPlayed_overall', 0),
                wins=stats.get('seasonWinsNum_overall', 0),
                draws=stats.get('seasonDrawsNum_overall', 0),
                losses=stats.get('seasonLossesNum_overall', 0),
                goals_scored=stats.get('seasonGoals_overall', 0),
                goals_conceded=stats.get('seasonConceded_overall', 0),
                points=stats.get('seasonPoints_overall', 0),
                ppg=stats.get('seasonPPG_overall', 0.0),
                position=team_data.get('table_position', 0),
                avg_goals_scored=stats.get('seasonScoredAVG_overall', 0.0),
                avg_goals_conceded=stats.get('seasonConcededAVG_overall', 0.0),
                avg_xg=stats.get('xg_for_avg_overall', 0.0),
                avg_xga=stats.get('xg_against_avg_overall', 0.0),
                xg_for_avg_overall=safe_float(stats.get('xg_for_avg_overall', 0.0)),
                xg_for_avg_home=safe_float(stats.get('xg_for_avg_home', 0.0)),
                xg_for_avg_away=safe_float(stats.get('xg_for_avg_away', 0.0)),
                xg_against_avg_overall=safe_float(stats.get('xg_against_avg_overall', 0.0)),
                xg_against_avg_home=safe_float(stats.get('xg_against_avg_home', 0.0)),
                xg_against_avg_away=safe_float(stats.get('xg_against_avg_away', 0.0)),
                home_attack_advantage=safe_int(stats.get('homeAttackAdvantage', 0)),
                home_defence_advantage=safe_int(stats.get('homeDefenceAdvantage', 0)),
                home_overall_advantage=safe_int(stats.get('homeOverallAdvantage', 0)),
                ht_ppg_overall=safe_float(stats.get('HTPPG_overall', 0.0)),
                ht_ppg_home=safe_float(stats.get('HTPPG_home', 0.0)),
                ht_ppg_away=safe_float(stats.get('HTPPG_away', 0.0)),
                leading_at_ht_percentage_overall=safe_float(stats.get('leadingAtHTPercentage_overall', 0.0)),
                leading_at_ht_percentage_home=safe_float(stats.get('leadingAtHTPercentage_home', 0.0)),
                leading_at_ht_percentage_away=safe_float(stats.get('leadingAtHTPercentage_away', 0.0)),
                drawing_at_ht_percentage_overall=safe_float(stats.get('drawingAtHTPercentage_overall', 0.0)),
                trailing_at_ht_percentage_overall=safe_float(stats.get('trailingAtHTPercentage_overall', 0.0)),
                clean_sheet_percentage_overall=safe_float(stats.get('seasonCSPercentage_overall', 0.0)),
                clean_sheet_percentage_home=safe_float(stats.get('seasonCSPercentage_home', 0.0)),
                clean_sheet_percentage_away=safe_float(stats.get('seasonCSPercentage_away', 0.0)),
                failed_to_score_percentage_overall=safe_float(stats.get('seasonFTSPercentage_overall', 0.0)),
                btts_percentage_overall=safe_float(stats.get('seasonBTTSPercentage_overall', 0.0)),
                btts_percentage_home=safe_float(stats.get('seasonBTTSPercentage_home', 0.0)),
                btts_percentage_away=safe_float(stats.get('seasonBTTSPercentage_away', 0.0)),
                over_25_percentage_overall=safe_float(stats.get('seasonOver25Percentage_overall', 0.0)),
                over_25_percentage_home=safe_float(stats.get('seasonOver25Percentage_home', 0.0)),
                over_25_percentage_away=safe_float(stats.get('seasonOver25Percentage_away', 0.0)),
                over_35_percentage_overall=safe_float(stats.get('seasonOver35Percentage_overall', 0.0)),
                highest_scored_home=safe_int(stats.get('seasonHighestScored_home', 0)),
                highest_conceded_home=safe_int(stats.get('seasonHighestConceded_home', 0)),
                highest_scored_away=safe_int(stats.get('seasonHighestScored_away', 0)),
                highest_conceded_away=safe_int(stats.get('seasonHighestConceded_away', 0)),
                season_goals_total_overall=safe_int(stats.get('seasonGoalsTotal_overall', 0)),
                season_goals_total_home=safe_int(stats.get('seasonGoalsTotal_home', 0)),
                season_goals_total_away=safe_int(stats.get('seasonGoalsTotal_away', 0)),
                season_matches_played_home=safe_int(stats.get('seasonMatchesPlayed_home', 0)),
                season_matches_played_away=safe_int(stats.get('seasonMatchesPlayed_away', 0)),
                win_percentage_overall=safe_float(stats.get('winPercentage_overall', 0.0)),
                win_percentage_home=safe_float(stats.get('winPercentage_home', 0.0)),
                win_percentage_away=safe_float(stats.get('winPercentage_away', 0.0)),
                draw_percentage_overall=safe_float(stats.get('drawPercentage_overall', 0.0)),
                draw_percentage_away=safe_float(stats.get('drawPercentage_away', 0.0)),
                lose_percentage_overall=safe_float(stats.get('losePercentage_overall', 0.0)),
                lose_percentage_home=safe_float(stats.get('losePercentage_home', 0.0)),
                lose_percentage_away=safe_float(stats.get('losePercentage_away', 0.0)),
            )
        except Exception as e:
            logger.error(f"Failed to get team stats for {team_id}: {e}")
            return None

    async def _get_h2h_data(self, match_id: int) -> Optional[dict]:
        """获取交锋记录（从 Match Details API）"""
        try:
            result = await self._get_match_details_cached(match_id)
            if not result or not result.get('success'):
                return None

            h2h = result.get('data', {}).get('h2h', {})
            if not h2h:
                return None

            prev_results = h2h.get('previous_matches_results', {})
            betting_stats = h2h.get('betting_stats', {})

            return {
                'total_matches': prev_results.get('totalMatches', 0),
                'home_wins': prev_results.get('team_a_wins', 0),
                'away_wins': prev_results.get('team_b_wins', 0),
                'draws': prev_results.get('draw', 0),
                'avg_goals': betting_stats.get('avg_goals', 0.0),
                'btts_pct': betting_stats.get('bttsPercentage', 0.0),
                'over_25_count': betting_stats.get('over25', 0),
                'over_25_pct': betting_stats.get('over25Percentage', 0.0),
                'btts_count': betting_stats.get('btts', 0),
                'total_goals': betting_stats.get('total_goals', 0),
            }
        except Exception as e:
            logger.error(f"Failed to get H2H data: {e}")
            return None

    async def get_recent_matches(self, days: int = 7) -> List[MatchBasicData]:
        """
        获取最近 N 天的比赛列表

        Args:
            days: 天数，默认 7 天

        Returns:
            MatchBasicData 列表
        """
        from datetime import timedelta

        matches = []

        for i in range(days):
            target_date = datetime.now() - timedelta(days=i)
            date_str = target_date.strftime('%Y-%m-%d')

            result = await self.provider.get_todays_matches(date=date_str)
            if result and result.get('success'):
                for match_data in result.get('data', []):
                    basic = self._parse_basic_data(match_data)
                    matches.append(basic)

        return matches