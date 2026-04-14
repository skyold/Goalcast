"""Sportmonks 数据转换模块"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from .models import Match, Team, Player, League, XGData, Odds, TeamForm, HeadToHead, Standings


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
