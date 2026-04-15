"""Sportmonks 数据转换模块"""

import re
from copy import deepcopy
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from .models import (
    Match,
    Team,
    Player,
    League,
    XGData,
    Odds,
    TeamForm,
    HeadToHead,
    Standings,
    SportmonksMatchSnapshot,
)

_ODDS_MOVEMENT_WINDOW_HOURS = 48
_EXPECTED_GOALS_TYPE_ID = 5304
_EXPECTED_GOALS_AGAINST_TYPE_ID = 9687
_EXPECTED_TYPE_LABELS = {
    5304: "xg",
    5305: "xgot",
    9684: "xgd",
    9686: "xg_prevented",
    9687: "xga",
    7940: "xg_shot",
    7941: "xg_non_shot",
}


class SportmonksTransformer:
    """Sportmonks 数据转换器"""
    
    def transform_match(self, match_data: Dict[str, Any]) -> Optional[Match]:
        """
        转换比赛数据
        
        Args:
            match_data: 原始比赛数据
            
        Returns:
            转换后的 Match 对象
        """
        try:
            match_id = match_data.get('id')
            if not match_id:
                return None
            
            # 提取日期和时间
            match_time = match_data.get('time', {})
            date = match_time.get('date', '')
            time = match_time.get('time', '')
            
            # 提取状态
            status = match_data.get('status', '')
            
            # 提取联赛信息
            league = match_data.get('league', {})
            league_id = league.get('id', 0)
            league_name = league.get('name', '')
            
            # 提取球队信息
            participants = match_data.get('participants', [])
            home_team_id = 0
            home_team_name = ''
            away_team_id = 0
            away_team_name = ''
            
            if len(participants) >= 2:
                home_team = participants[0]
                away_team = participants[1]
                home_team_id = home_team.get('id', 0)
                home_team_name = home_team.get('name', '')
                away_team_id = away_team.get('id', 0)
                away_team_name = away_team.get('name', '')
            
            # 提取比分
            scores = match_data.get('scores', {})
            home_score = scores.get('home', 0)
            away_score = scores.get('away', 0)
            
            # 提取场馆和裁判
            venue_id = match_data.get('venue_id')
            referee_id = match_data.get('referee_id')
            
            return Match(
                match_id=match_id,
                date=date,
                time=time,
                status=status,
                league_id=league_id,
                league_name=league_name,
                home_team_id=home_team_id,
                home_team_name=home_team_name,
                away_team_id=away_team_id,
                away_team_name=away_team_name,
                home_score=home_score,
                away_score=away_score,
                venue_id=venue_id,
                referee_id=referee_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        except Exception as e:
            print(f"Error transforming match data: {e}")
            return None
    
    def transform_team(self, team_data: Dict[str, Any]) -> Optional[Team]:
        """
        转换球队数据
        
        Args:
            team_data: 原始球队数据
            
        Returns:
            转换后的 Team 对象
        """
        try:
            team_id = team_data.get('id')
            if not team_id:
                return None
            
            name = team_data.get('name', '')
            short_name = team_data.get('short_code') or team_data.get('abbreviation')
            logo = team_data.get('logo')
            country = team_data.get('country', {}).get('name')
            
            return Team(
                team_id=team_id,
                name=name,
                short_name=short_name,
                logo=logo,
                country=country,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        except Exception as e:
            print(f"Error transforming team data: {e}")
            return None
    
    def transform_player(self, player_data: Dict[str, Any]) -> Optional[Player]:
        """
        转换球员数据
        
        Args:
            player_data: 原始球员数据
            
        Returns:
            转换后的 Player 对象
        """
        try:
            player_id = player_data.get('id')
            if not player_id:
                return None
            
            name = player_data.get('name', '')
            position = player_data.get('position')
            team_id = player_data.get('team_id')
            nationality = player_data.get('nationality')
            birth_date = player_data.get('birthdate')
            
            return Player(
                player_id=player_id,
                name=name,
                position=position,
                team_id=team_id,
                nationality=nationality,
                birth_date=birth_date,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        except Exception as e:
            print(f"Error transforming player data: {e}")
            return None
    
    def transform_league(self, league_data: Dict[str, Any]) -> Optional[League]:
        """
        转换联赛数据
        
        Args:
            league_data: 原始联赛数据
            
        Returns:
            转换后的 League 对象
        """
        try:
            league_id = league_data.get('id')
            if not league_id:
                return None
            
            name = league_data.get('name', '')
            country = league_data.get('country', {}).get('name')
            season_id = league_data.get('current_season_id')
            season_name = league_data.get('current_season', {}).get('name')
            
            return League(
                league_id=league_id,
                name=name,
                country=country,
                season_id=season_id,
                season_name=season_name,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        except Exception as e:
            print(f"Error transforming league data: {e}")
            return None
    
    def transform_xg_data(self, match_id: int, xg_data: Dict[str, Any]) -> Optional[XGData]:
        """
        转换 xG 数据
        
        Args:
            match_id: 比赛 ID
            xg_data: 原始 xG 数据
            
        Returns:
            转换后的 XGData 对象
        """
        try:
            data = xg_data.get('data', [])
            if not data:
                return None
            
            # 提取 xG 数据
            home_xg = 0.0
            away_xg = 0.0
            home_xg_against = 0.0
            away_xg_against = 0.0
            
            for item in data:
                if item.get('type') == 'expected_goals':
                    home_xg = float(item.get('home', 0.0))
                    away_xg = float(item.get('away', 0.0))
                elif item.get('type') == 'expected_goals_against':
                    home_xg_against = float(item.get('home', 0.0))
                    away_xg_against = float(item.get('away', 0.0))
            
            return XGData(
                match_id=match_id,
                home_xg=home_xg,
                away_xg=away_xg,
                home_xg_against=home_xg_against,
                away_xg_against=away_xg_against,
                source='sportmonks',
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        except Exception as e:
            print(f"Error transforming xG data: {e}")
            return None
    
    @staticmethod
    def _parse_ah_line(label: str) -> Optional[float]:
        """
        从 Sportmonks Asian Handicap outcome label 中解析让球线数值。

        Sportmonks 常见 label 格式：
          - "Home -0.5"  → -0.5  （主队让半球）
          - "Away -0.5"  → +0.5  （客队让半球，即主队受让 +0.5）
          - "Home -1"    → -1.0
          - "Home -0.25" → -0.25 （四分之一盘，上下盘各半）
          - "Home -0.75" → -0.75
          - "Home 0"     → 0.0   （平手盘）

        返回值含义：负值 = 主队让球，正值 = 主队受让（客队让球）。
        无法解析时返回 None。
        """
        import re
        if not label:
            return None
        label = label.strip()
        # 匹配 "Home <数字>" 或 "Away <数字>"
        m = re.match(r'^(Home|Away)\s+([+-]?\d+(?:\.\d+)?)$', label, re.IGNORECASE)
        if not m:
            return None
        side = m.group(1).lower()
        value = float(m.group(2))
        # Away label 的让球线方向与 Home 相反
        return value if side == 'home' else -value

    def transform_odds(self, match_id: int, odds_data: Dict[str, Any]) -> List[Odds]:
        """
        转换赔率数据

        Args:
            match_id: 比赛 ID
            odds_data: 原始赔率数据

        Returns:
            转换后的 Odds 对象列表

        亚盘 (Asian Handicap) 说明：
            Sportmonks 将每个让球线作为独立 market 返回，market_name="Asian Handicap"，
            outcomes 通常为两项：
              {"label": "Home -0.5", "odds": 1.85}
              {"label": "Away -0.5", "odds": 1.95}
            本函数取概率最高的让球线（通常为最接近平局的主盘线）存入 Odds 对象。
            如果同一 bookmaker 下存在多个 AH 让球线，选取让球线绝对值最小的（即主线）。
        """
        odds_list = []
        try:
            data = odds_data.get('data', [])
            for item in data:
                bookmaker = item.get('bookmaker', {}).get('name')
                markets = item.get('markets', [])

                # 提取标准欧盘赔率
                home_win = 0.0
                draw = 0.0
                away_win = 0.0
                over_25 = 0.0
                under_25 = 0.0
                btts_yes = 0.0
                btts_no = 0.0

                # 亚盘候选：{abs(ah_line): (ah_line, ah_home_odds, ah_away_odds)}
                ah_candidates: Dict[float, tuple] = {}

                for market in markets:
                    market_name = market.get('name')
                    outcomes = market.get('outcomes', [])

                    if market_name == 'Match Odds':
                        for outcome in outcomes:
                            if outcome.get('label') == 'Home':
                                home_win = float(outcome.get('odds', 0.0))
                            elif outcome.get('label') == 'Draw':
                                draw = float(outcome.get('odds', 0.0))
                            elif outcome.get('label') == 'Away':
                                away_win = float(outcome.get('odds', 0.0))

                    elif market_name == 'Over/Under':
                        for outcome in outcomes:
                            if outcome.get('label') == 'Over 2.5':
                                over_25 = float(outcome.get('odds', 0.0))
                            elif outcome.get('label') == 'Under 2.5':
                                under_25 = float(outcome.get('odds', 0.0))

                    elif market_name == 'Both Teams To Score':
                        for outcome in outcomes:
                            if outcome.get('label') == 'Yes':
                                btts_yes = float(outcome.get('odds', 0.0))
                            elif outcome.get('label') == 'No':
                                btts_no = float(outcome.get('odds', 0.0))

                    elif market_name == 'Asian Handicap':
                        # 每个 Asian Handicap market 条目对应一条让球线，含两个 outcome
                        ah_home_odds_val = 0.0
                        ah_away_odds_val = 0.0
                        ah_line_val: Optional[float] = None

                        for outcome in outcomes:
                            label = outcome.get('label', '')
                            raw_odds = float(outcome.get('odds', 0.0))
                            parsed_line = self._parse_ah_line(label)
                            if parsed_line is None:
                                continue
                            label_lower = label.strip().lower()
                            if label_lower.startswith('home'):
                                ah_line_val = parsed_line
                                ah_home_odds_val = raw_odds
                            elif label_lower.startswith('away'):
                                ah_away_odds_val = raw_odds

                        if (
                            ah_line_val is not None
                            and ah_home_odds_val > 1.0
                            and ah_away_odds_val > 1.0
                        ):
                            key = abs(ah_line_val)
                            # 保留绝对值最小的让球线（主盘线）
                            if key not in ah_candidates or key < min(ah_candidates.keys()):
                                ah_candidates[key] = (ah_line_val, ah_home_odds_val, ah_away_odds_val)

                # 选主盘线：绝对值最小的让球线
                ah_line_final = None
                ah_home_final = None
                ah_away_final = None
                if ah_candidates:
                    best_key = min(ah_candidates.keys())
                    ah_line_final, ah_home_final, ah_away_final = ah_candidates[best_key]

                if home_win > 0 and draw > 0 and away_win > 0:
                    odds = Odds(
                        match_id=match_id,
                        home_win=home_win,
                        draw=draw,
                        away_win=away_win,
                        over_25=over_25 if over_25 > 0 else None,
                        under_25=under_25 if under_25 > 0 else None,
                        btts_yes=btts_yes if btts_yes > 0 else None,
                        btts_no=btts_no if btts_no > 0 else None,
                        ah_line=ah_line_final,
                        ah_home_odds=ah_home_final,
                        ah_away_odds=ah_away_final,
                        bookmaker=bookmaker,
                        timestamp=datetime.now(),
                        created_at=datetime.now()
                    )
                    odds_list.append(odds)
        except Exception as e:
            print(f"Error transforming odds data: {e}")

        return odds_list
    
    def transform_team_form(self, team_id: int, match_id: int, form_data: Dict[str, Any]) -> Optional[TeamForm]:
        """
        转换球队状态数据
        
        Args:
            team_id: 球队 ID
            match_id: 比赛 ID
            form_data: 原始球队状态数据
            
        Returns:
            转换后的 TeamForm 对象
        """
        try:
            data = form_data.get('data', [])
            if not data:
                return None
            
            # 计算最近 5 场和 10 场的状态
            recent_matches = data[:10]  # 最近 10 场比赛
            form_5 = ''
            form_10 = ''
            goals_for = 0
            goals_against = 0
            points = 0
            
            for i, match in enumerate(recent_matches):
                home_team_id = match.get('localteam_id')
                away_team_id = match.get('visitorteam_id')
                home_score = match.get('localteam_score', 0)
                away_score = match.get('visitorteam_score', 0)
                
                # 计算球队在这场比赛的结果
                if team_id == home_team_id:
                    goals_for += home_score
                    goals_against += away_score
                    if home_score > away_score:
                        form_10 += 'W'
                        points += 3
                    elif home_score == away_score:
                        form_10 += 'D'
                        points += 1
                    else:
                        form_10 += 'L'
                elif team_id == away_team_id:
                    goals_for += away_score
                    goals_against += home_score
                    if away_score > home_score:
                        form_10 += 'W'
                        points += 3
                    elif away_score == home_score:
                        form_10 += 'D'
                        points += 1
                    else:
                        form_10 += 'L'
            
            # 提取最近 5 场的状态
            form_5 = form_10[:5] if len(form_10) >= 5 else form_10
            
            return TeamForm(
                team_id=team_id,
                match_id=match_id,
                form_5=form_5,
                form_10=form_10,
                goals_for=goals_for,
                goals_against=goals_against,
                points=points,
                created_at=datetime.now()
            )
        except Exception as e:
            print(f"Error transforming team form data: {e}")
            return None
    
    def transform_head_to_head(self, home_team_id: int, away_team_id: int, h2h_data: Dict[str, Any]) -> Optional[HeadToHead]:
        """
        转换交锋记录数据
        
        Args:
            home_team_id: 主队 ID
            away_team_id: 客队 ID
            h2h_data: 原始交锋记录数据
            
        Returns:
            转换后的 HeadToHead 对象
        """
        try:
            data = h2h_data.get('data', [])
            matches = len(data)
            home_wins = 0
            draws = 0
            away_wins = 0
            home_goals = 0
            away_goals = 0
            
            for match in data:
                home_score = match.get('localteam_score', 0)
                away_score = match.get('visitorteam_score', 0)
                home_goals += home_score
                away_goals += away_score
                
                if home_score > away_score:
                    home_wins += 1
                elif home_score == away_score:
                    draws += 1
                else:
                    away_wins += 1
            
            return HeadToHead(
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                matches=matches,
                home_wins=home_wins,
                draws=draws,
                away_wins=away_wins,
                home_goals=home_goals,
                away_goals=away_goals,
                created_at=datetime.now()
            )
        except Exception as e:
            print(f"Error transforming head-to-head data: {e}")
            return None
    
    def transform_standings(self, league_id: int, standings_data: Dict[str, Any]) -> List[Standings]:
        """
        转换积分榜数据
        
        Args:
            league_id: 联赛 ID
            standings_data: 原始积分榜数据
            
        Returns:
            转换后的 Standings 对象列表
        """
        standings_list = []
        try:
            data = standings_data.get('data', [])
            for item in data:
                position = item.get('position', 0)
                team_id = item.get('team_id', 0)
                points = item.get('points', 0)
                matches_played = item.get('matches_played', 0)
                wins = item.get('wins', 0)
                draws = item.get('draws', 0)
                losses = item.get('losses', 0)
                goals_for = item.get('goals_for', 0)
                goals_against = item.get('goals_against', 0)
                goal_difference = item.get('goal_difference', 0)
                season_id = item.get('season_id')
                
                standings = Standings(
                    league_id=league_id,
                    team_id=team_id,
                    position=position,
                    points=points,
                    matches_played=matches_played,
                    wins=wins,
                    draws=draws,
                    losses=losses,
                    goals_for=goals_for,
                    goals_against=goals_against,
                    goal_difference=goal_difference,
                    season_id=season_id,
                    created_at=datetime.now()
                )
                standings_list.append(standings)
        except Exception as e:
            print(f"Error transforming standings data: {e}")
        
        return standings_list
    
    def transform_all_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换所有数据
        
        Args:
            extracted_data: 提取的原始数据
            
        Returns:
            转换后的结构化数据
        """
        transformed_data = {
            'matches': [],
            'teams': [],
            'players': [],
            'leagues': [],
            'xg_data': [],
            'odds': [],
            'team_forms': [],
            'head_to_head': [],
            'standings': []
        }
        
        # 转换比赛数据
        for match_data in extracted_data.get('matches', []):
            # 处理从 JSON 文件提取的数据
            if isinstance(match_data, dict) and 'id' in match_data:
                match = self.transform_match(match_data)
                if match:
                    transformed_data['matches'].append(match)
            # 处理从数据库提取的数据
            elif isinstance(match_data, dict) and 'data' in match_data:
                match = self.transform_match(match_data['data'])
                if match:
                    transformed_data['matches'].append(match)
        
        # 转换扩展数据
        extended_data = extracted_data.get('extended_data', {})
        for match_id_str, ext_data in extended_data.items():
            match_id = int(match_id_str)
            
            # 转换 xG 数据
            xg_data = ext_data.get('xg')
            if xg_data:
                xg = self.transform_xg_data(match_id, xg_data)
                if xg:
                    transformed_data['xg_data'].append(xg)
            
            # 转换预测数据
            # 预测数据暂时不需要单独转换，可在需要时添加
            
            # 转换交锋记录数据
            h2h_data = ext_data.get('head_to_head')
            if h2h_data:
                # 尝试从扩展数据中获取球队 ID
                home_team_id = None
                away_team_id = None
                # 这里需要根据实际数据结构调整
                h2h = self.transform_head_to_head(home_team_id or 0, away_team_id or 0, h2h_data)
                if h2h:
                    transformed_data['head_to_head'].append(h2h)
            
            # 转换球队状态数据
            home_form_data = ext_data.get('home_form')
            away_form_data = ext_data.get('away_form')
            if home_form_data:
                # 尝试从扩展数据中获取球队 ID
                home_team_id = None
                # 这里需要根据实际数据结构调整
                home_form = self.transform_team_form(home_team_id or 0, match_id, home_form_data)
                if home_form:
                    transformed_data['team_forms'].append(home_form)
            if away_form_data:
                # 尝试从扩展数据中获取球队 ID
                away_team_id = None
                # 这里需要根据实际数据结构调整
                away_form = self.transform_team_form(away_team_id or 0, match_id, away_form_data)
                if away_form:
                    transformed_data['team_forms'].append(away_form)
            
            # 转换积分榜数据
            standings_data = ext_data.get('standings')
            if standings_data:
                # 尝试从扩展数据中获取联赛 ID
                league_id = None
                # 这里需要根据实际数据结构调整
                standings_list = self.transform_standings(league_id or 0, standings_data)
                transformed_data['standings'].extend(standings_list)
        
        # 转换从数据库提取的特定数据
        for match_id, xg_data in extracted_data.get('xg_data', {}).items():
            xg = self.transform_xg_data(match_id, xg_data)
            if xg:
                transformed_data['xg_data'].append(xg)
        
        for match_id, team_form_data in extracted_data.get('team_form', {}).items():
            home_team_id = team_form_data.get('home_team_id')
            away_team_id = team_form_data.get('away_team_id')
            home_form_data = team_form_data.get('home_form')
            away_form_data = team_form_data.get('away_form')
            
            if home_team_id and home_form_data:
                home_form = self.transform_team_form(home_team_id, match_id, home_form_data)
                if home_form:
                    transformed_data['team_forms'].append(home_form)
            if away_team_id and away_form_data:
                away_form = self.transform_team_form(away_team_id, match_id, away_form_data)
                if away_form:
                    transformed_data['team_forms'].append(away_form)
        
        for match_id, h2h_data in extracted_data.get('head_to_head', {}).items():
            home_team_id = h2h_data.get('home_team_id')
            away_team_id = h2h_data.get('away_team_id')
            data = h2h_data.get('data')
            if home_team_id and away_team_id and data:
                h2h = self.transform_head_to_head(home_team_id, away_team_id, data)
                if h2h:
                    transformed_data['head_to_head'].append(h2h)
        
        for match_id, standings_data in extracted_data.get('standings', {}).items():
            league_id = standings_data.get('league_id')
            data = standings_data.get('data')
            if league_id and data:
                standings_list = self.transform_standings(league_id, data)
                transformed_data['standings'].extend(standings_list)
        
        return transformed_data


_SNAPSHOT_LAYERS = (
    "xg",
    "standings",
    "odds",
    "asian_handicap",
    "odds_movement",
    "lineups",
    "h2h",
    "predictions",
)


def build_match_snapshot(
    raw_layers: Dict[str, Any],
    existing_snapshot: Optional[Dict[str, Any]] = None,
) -> SportmonksMatchSnapshot:
    """将原始分层数据组装为 Sportmonks 单场比赛快照。"""
    snapshot = deepcopy(existing_snapshot or {})
    fixture = raw_layers.get("fixture") or {}

    participants = fixture.get("participants", []) if isinstance(fixture, dict) else []
    home = next(
        (
            item for item in participants
            if isinstance(item, dict) and isinstance(item.get("meta"), dict)
            and item["meta"].get("location") == "home"
        ),
        {},
    )
    away = next(
        (
            item for item in participants
            if isinstance(item, dict) and isinstance(item.get("meta"), dict)
            and item["meta"].get("location") == "away"
        ),
        {},
    )

    if fixture:
        snapshot.update(
            {
                "fixture_id": fixture.get("id", snapshot.get("fixture_id")),
                "match_date": str(fixture.get("starting_at", snapshot.get("match_date", "")))[:10],
                "kickoff_time": fixture.get("starting_at", snapshot.get("kickoff_time", "")),
                "league": (fixture.get("league") or {}).get("name", snapshot.get("league", "")),
                "season_id": fixture.get("season_id", snapshot.get("season_id")),
                "home_team": home.get("name", snapshot.get("home_team", "")),
                "away_team": away.get("name", snapshot.get("away_team", "")),
                "home_team_id": home.get("id", snapshot.get("home_team_id")),
                "away_team_id": away.get("id", snapshot.get("away_team_id")),
            }
        )

    if "xg" in raw_layers:
        snapshot["xg"] = raw_layers.get("xg")
    if "standings" in raw_layers:
        snapshot["standings"] = raw_layers.get("standings")
    if "odds" in raw_layers:
        snapshot["odds"] = raw_layers.get("odds")
    if "asian_handicap" in raw_layers:
        snapshot["asian_handicap"] = raw_layers.get("asian_handicap")
    if "odds_movement" in raw_layers:
        snapshot["odds_movement"] = raw_layers.get("odds_movement")
    if "lineups" in raw_layers:
        snapshot["lineups"] = raw_layers.get("lineups")
    if "h2h" in raw_layers:
        snapshot["h2h"] = raw_layers.get("h2h")
    if "predictions" in raw_layers:
        snapshot["predictions"] = raw_layers.get("predictions")

    available_layers = tuple(layer for layer in _SNAPSHOT_LAYERS if snapshot.get(layer) is not None)
    missing_layers = tuple(layer for layer in _SNAPSHOT_LAYERS if snapshot.get(layer) is None)
    cache_status = "fresh" if not missing_layers else "partial"

    snapshot["available_layers"] = available_layers
    snapshot["missing_layers"] = missing_layers
    snapshot["cache_status"] = cache_status
    snapshot["overall_quality"] = snapshot.get("overall_quality", _compute_quality(available_layers))

    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    snapshot["warmed_at"] = snapshot.get("warmed_at", now_iso)
    snapshot["updated_at"] = now_iso
    snapshot["expires_at"] = snapshot.get("expires_at")
    snapshot["source_versions"] = snapshot.get("source_versions", {"sportmonks": "v3"})

    return SportmonksMatchSnapshot(**snapshot)


def _compute_quality(available_layers: tuple[str, ...]) -> float:
    if not available_layers:
        return 0.0
    weights = {
        "xg": 0.20,
        "standings": 0.10,
        "odds": 0.20,
        "asian_handicap": 0.10,
        "odds_movement": 0.10,
        "lineups": 0.10,
        "h2h": 0.10,
        "predictions": 0.10,
    }
    return round(sum(weights.get(layer, 0.0) for layer in available_layers), 3)


# --- 迁移自 sportmonks_resolver.py 的辅助提取函数 ---

def _extract_team_xg_avg(raw: Any, participant_id: Optional[int] = None) -> Optional[dict]:
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

    entries = [entry for entry in data if isinstance(entry, dict)]
    if participant_id is not None:
        matching_entries = [
            entry for entry in entries
            if str(entry.get("participant_id")) == str(participant_id)
        ]
        if matching_entries:
            entries = matching_entries
        elif any(entry.get("participant_id") is not None for entry in entries):
            return None

    xg_values: list[float] = []
    xga_values: list[float] = []

    for entry in entries:
        # Sportmonks v3 field names vary by subscription tier
        nested_data = entry.get("data") if isinstance(entry.get("data"), dict) else {}
        type_id = entry.get("type_id")
        xg_val = (
            entry.get("xg")
            or entry.get("expected_goals")
        )
        xga_val = (
            entry.get("xga")
            or entry.get("expected_goals_against")
        )

        if xg_val is None and type_id == _EXPECTED_GOALS_TYPE_ID:
            xg_val = nested_data.get("value") or entry.get("value")
        if xga_val is None and type_id == _EXPECTED_GOALS_AGAINST_TYPE_ID:
            xga_val = (
                nested_data.get("value")
                or nested_data.get("xga")
                or nested_data.get("expected_goals_against")
                or entry.get("value")
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

    # 增强逻辑：按 bookmaker 分组提取 1x2 赔率
    bookmaker_odds = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        
        # 提取赔率值，尝试多种可能的键名
        market_id = item.get("market_id")
        market_name = str(item.get("market_name") or item.get("market_description") or "").lower()
        
        # 如果是 Match Odds 盘口 (1x2)
        if market_id == 1 or any(m in market_name for m in ("match odds", "3way result", "fulltime result")):
            label = str(item.get("label") or item.get("name") or "").lower()
            val = _to_float(item.get("value") or item.get("odds") or item.get("dp3"))
            bookmaker_id = item.get("bookmaker_id") or "default"
            
            if val > 1.0:
                norm = _normalize_1x2_label(label)
                if norm:
                    if bookmaker_id not in bookmaker_odds:
                        bookmaker_odds[bookmaker_id] = {}
                    bookmaker_odds[bookmaker_id][norm] = val
                    
                    # 如果该博彩公司凑齐了 1x2，立即返回
                    if {"home_win", "draw", "away_win"} <= set(bookmaker_odds[bookmaker_id]):
                        return {
                            "home_win": bookmaker_odds[bookmaker_id]["home_win"],
                            "draw": bookmaker_odds[bookmaker_id]["draw"],
                            "away_win": bookmaker_odds[bookmaker_id]["away_win"],
                            "bookmaker_id": bookmaker_id
                        }

    # 原始逻辑作为兜底
    for item in data:
        if not isinstance(item, dict):
            continue
        odds = item.get("odds") or item
        home = _to_float(odds.get("home") or odds.get("dp3"))
        draw = _to_float(odds.get("draw") or odds.get("dp1"))
        away = _to_float(odds.get("away") or odds.get("dp2"))
        if home > 1.0 and draw > 1.0 and away > 1.0:
            return {"home_win": home, "draw": draw, "away_win": away}

    preferred_markets = ("fulltime result", "full time result", "3way result", "match winner")
    fallback_markets = ("result", "winner")
    for market_group in (preferred_markets, fallback_markets):
        market_values: dict[str, float] = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            market_desc = str(item.get("market_description") or item.get("market_name") or "").lower()
            if "handicap" in market_desc:
                continue
            if market_group is preferred_markets:
                if market_desc not in preferred_markets:
                    continue
            else:
                if not any(token in market_desc for token in fallback_markets):
                    continue
            label = str(item.get("label") or item.get("name") or "").strip().lower()
            value = _to_float(item.get("value") or item.get("dp3"))
            if value <= 1.0:
                continue
            normalized = _normalize_1x2_label(label)
            if normalized is not None and normalized not in market_values:
                market_values[normalized] = value

        if {"home_win", "draw", "away_win"} <= set(market_values):
            return {
                "home_win": market_values["home_win"],
                "draw": market_values["draw"],
                "away_win": market_values["away_win"],
            }
    return None


def _extract_sportmonks_asian_handicap_local(raw: Any) -> Optional[dict]:
    data = (
        raw.get("data", [])
        if isinstance(raw, dict)
        else (raw if isinstance(raw, list) else [])
    )
    candidates: dict[float, dict[str, float]] = {}

    for item in data:
        if not isinstance(item, dict):
            continue
        market_desc = str(item.get("market_description") or item.get("market_name") or "").lower()
        if "asian handicap" not in market_desc or "corners" in market_desc or "1st half" in market_desc:
            continue
        label = str(item.get("label") or item.get("name") or "").strip()
        parsed_line = _parse_ah_label(
            str(item.get("original_label") or item.get("handicap") or label)
        )
        value = _to_float(item.get("value") or item.get("dp3"))
        if parsed_line is None or value <= 1.0:
            continue

        key = abs(parsed_line)
        candidate = candidates.setdefault(key, {})
        candidate["bookmaker_id"] = item.get("bookmaker_id") or candidate.get("bookmaker_id")
        label_lower = label.lower()
        if label_lower.startswith("home"):
            candidate["ah_line"] = parsed_line
            candidate["ah_home_odds"] = value
        elif label_lower.startswith("away"):
            candidate["ah_line"] = candidate.get("ah_line", parsed_line)
            candidate["ah_away_odds"] = value

    for key in sorted(candidates):
        candidate = candidates[key]
        if {"ah_line", "ah_home_odds", "ah_away_odds"} <= set(candidate):
            return {
                "ah_line": candidate["ah_line"],
                "ah_home_odds": candidate["ah_home_odds"],
                "ah_away_odds": candidate["ah_away_odds"],
                "bookmaker_id": candidate.get("bookmaker_id")
            }
    return None


def _normalize_1x2_label(label: str) -> Optional[str]:
    mapping = {
        "1": "home_win",
        "home": "home_win",
        "x": "draw",
        "draw": "draw",
        "2": "away_win",
        "away": "away_win",
    }
    return mapping.get(label)


def _parse_ah_label(label: str) -> Optional[float]:
    if re.match(r"^[+-]?\d+(?:\.\d+)?$", label.strip()):
        return float(label)
    match = re.match(r"^(Home|Away)\s+([+-]?\d+(?:\.\d+)?)$", label, re.IGNORECASE)
    if not match:
        return None
    side = match.group(1).lower()
    value = float(match.group(2))
    return value if side == "home" else -value


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


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


def _extract_predictions(raw: Any) -> Optional[dict]:
    """
    Extract match probability predictions from Sportmonks.
    Returns: {"home_win": float, "draw": float, "away_win": float}
    """
    if not raw or not isinstance(raw, dict):
        return None
    data = raw.get("data", [])
    if not data:
        return None

    for item in data:
        if not isinstance(item, dict):
            continue
        predictions = item.get("predictions")
        if isinstance(predictions, dict):
            home = predictions.get("home") or predictions.get("1")
            draw = predictions.get("draw") or predictions.get("X") or predictions.get("x")
            away = predictions.get("away") or predictions.get("2")
            if home is not None and draw is not None and away is not None:
                # Normalise to 0.0 - 1.0 if they are percentages
                total = float(home) + float(draw) + float(away)
                if total > 0:
                    return {
                        "home_win": float(home) / total,
                        "draw": float(draw) / total,
                        "away_win": float(away) / total,
                    }
    return None


def _build_sportmonks_xg_payload(
    fixture_raw: Any,
    home_participant_id: Optional[int],
    away_participant_id: Optional[int],
    home_history_raw: Any = None,
    away_history_raw: Any = None,
) -> Optional[dict]:
    fixture_entries = _extract_fixture_expected_entries(fixture_raw)
    fixture_home = _build_expected_side_payload(
        fixture_entries,
        participant_id=home_participant_id,
        fallback_location="home",
    )
    fixture_away = _build_expected_side_payload(
        fixture_entries,
        participant_id=away_participant_id,
        fallback_location="away",
    )
    home_history = _build_expected_side_payload(
        (home_history_raw or {}).get("data", []) if isinstance(home_history_raw, dict) else [],
        participant_id=home_participant_id,
        fallback_location="home",
    )
    away_history = _build_expected_side_payload(
        (away_history_raw or {}).get("data", []) if isinstance(away_history_raw, dict) else [],
        participant_id=away_participant_id,
        fallback_location="away",
    )
    lineup_home = _extract_lineup_expected_entries(fixture_raw, team_id=home_participant_id)
    lineup_away = _extract_lineup_expected_entries(fixture_raw, team_id=away_participant_id)

    summary = _build_xg_summary(fixture_home, fixture_away)
    summary_source = "fixture_expected"
    if summary is None:
        summary = _build_xg_summary(home_history, away_history)
        summary_source = "team_expected_history"

    type_ids = sorted(
        {
            *(_collect_expected_type_ids(fixture_entries)),
            *(_collect_expected_type_ids((home_history or {}).get("entries", []))),
            *(_collect_expected_type_ids((away_history or {}).get("entries", []))),
            *(_collect_lineup_expected_type_ids(lineup_home)),
            *(_collect_lineup_expected_type_ids(lineup_away)),
        }
    )

    has_payload = any(
        [
            fixture_home,
            fixture_away,
            home_history,
            away_history,
            lineup_home,
            lineup_away,
            summary,
        ]
    )
    if not has_payload:
        return None

    payload: dict[str, Any] = {
        "summary_source": summary_source if summary is not None else None,
        "available_type_ids": type_ids,
        "fixture_expected": {
            "entries": fixture_entries,
            "home": fixture_home,
            "away": fixture_away,
        },
        "lineup_expected": {
            "home": lineup_home,
            "away": lineup_away,
        },
        "team_expected_history": {
            "home": home_history,
            "away": away_history,
        },
    }
    if summary is not None:
        payload.update(summary)
    return payload


def _extract_fixture_expected_entries(fixture_raw: Any) -> list[dict[str, Any]]:
    if not isinstance(fixture_raw, dict):
        return []
    data = fixture_raw.get("data")
    if not isinstance(data, dict):
        return []
    entries = data.get("expected", [])
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _extract_lineup_expected_entries(fixture_raw: Any, team_id: Optional[int]) -> list[dict[str, Any]]:
    if team_id is None or not isinstance(fixture_raw, dict):
        return []
    data = fixture_raw.get("data")
    if not isinstance(data, dict):
        return []
    lineups = data.get("lineups", [])
    if not isinstance(lineups, list):
        return []

    result: list[dict[str, Any]] = []
    for entry in lineups:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("team_id")) != str(team_id):
            continue
        expected = entry.get("expected")
        if not isinstance(expected, list) or not expected:
            continue
        result.append(
            {
                "team_id": entry.get("team_id"),
                "player_id": entry.get("player_id"),
                "lineup_id": entry.get("lineup_id"),
                "player_name": entry.get("player_name"),
                "expected": [item for item in expected if isinstance(item, dict)],
            }
        )
    return result


def _build_expected_side_payload(
    entries: list[dict[str, Any]],
    participant_id: Optional[int],
    fallback_location: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    if participant_id is None:
        return None
    filtered = [
        entry for entry in entries
        if isinstance(entry, dict) and str(entry.get("participant_id")) == str(participant_id)
    ]
    if not filtered:
        return None

    # 应用 xG 映射逻辑
    metrics = _aggregate_expected_metrics(filtered)

    return {
        "participant_id": participant_id,
        "location": filtered[0].get("location") or fallback_location,
        "metrics": metrics,
        "entries": filtered,
    }


def _aggregate_expected_metrics(entries: list[dict[str, Any]]) -> dict[str, float]:
    grouped: dict[int, list[float]] = {}
    for entry in entries:
        type_id = entry.get("type_id")
        value = _extract_expected_value(entry)
        try:
            type_id_int = int(type_id)
        except (TypeError, ValueError):
            continue
        if value is None:
            continue
        grouped.setdefault(type_id_int, []).append(value)

    metrics: dict[str, float] = {}
    for type_id, values in grouped.items():
        if not values:
            continue
        avg_val = sum(values) / len(values)
        metrics[str(type_id)] = avg_val
        
        # 标签映射
        label = _EXPECTED_TYPE_LABELS.get(type_id)
        if label:
            metrics[label] = avg_val
            
    # 特殊逻辑：如果缺少标准的 5304 xG，但存在 9686 (xG Prevented) 或 7940 (xG Shot)，进行兜底映射
    if "xg" not in metrics:
        if "xg_shot" in metrics:
             metrics["xg"] = metrics["xg_shot"]
        elif "xg_prevented" in metrics:
             metrics["xg"] = metrics["xg_prevented"]
             
    if "xga" not in metrics and "xg_non_shot" in metrics:
        metrics["xga"] = metrics["xg_non_shot"]
        
    return metrics


def _extract_expected_value(entry: dict[str, Any]) -> Optional[float]:
    nested_data = entry.get("data") if isinstance(entry.get("data"), dict) else {}
    value = nested_data.get("value")
    if value is None:
        value = entry.get("value")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _build_xg_summary(home_payload: Optional[dict], away_payload: Optional[dict]) -> Optional[dict[str, float]]:
    if not home_payload or not away_payload:
        return None
    home_metrics = home_payload.get("metrics") or {}
    away_metrics = away_payload.get("metrics") or {}
    home_xg = home_metrics.get("xg") or home_metrics.get(str(_EXPECTED_GOALS_TYPE_ID))
    away_xg = away_metrics.get("xg") or away_metrics.get(str(_EXPECTED_GOALS_TYPE_ID))
    home_xga = home_metrics.get("xga") or home_metrics.get(str(_EXPECTED_GOALS_AGAINST_TYPE_ID))
    away_xga = away_metrics.get("xga") or away_metrics.get(str(_EXPECTED_GOALS_AGAINST_TYPE_ID))
    
    if home_xg is None or away_xg is None:
        return None
        
    return {
        "home_xg_for": home_xg,
        "home_xg_against": home_xga,
        "away_xg_for": away_xg,
        "away_xg_against": away_xga,
    }


def _collect_expected_type_ids(entries: list[dict[str, Any]]) -> set[int]:
    type_ids: set[int] = set()
    for entry in entries:
        type_id = entry.get("type_id")
        if isinstance(type_id, int):
            type_ids.add(type_id)
    return type_ids


def _collect_lineup_expected_type_ids(players: list[dict[str, Any]]) -> set[int]:
    type_ids: set[int] = set()
    for player in players:
        expected = player.get("expected", [])
        if not isinstance(expected, list):
            continue
        type_ids.update(_collect_expected_type_ids([item for item in expected if isinstance(item, dict)]))
    return type_ids
