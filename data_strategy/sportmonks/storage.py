"""Sportmonks 数据存储模块"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from .models import Match, Team, Player, League, XGData, Odds, TeamForm, HeadToHead, Standings


class SportmonksStorage:
    """Sportmonks 数据存储"""
    
    def __init__(self, db_path: Path):
        """
        初始化存储
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._initialize_db()
    
    def _initialize_db(self):
        """
        初始化数据库，创建必要的表
        """
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # 创建比赛表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sportmonks_matches (
                match_id INTEGER PRIMARY KEY,
                date TEXT,
                time TEXT,
                status TEXT,
                league_id INTEGER,
                league_name TEXT,
                home_team_id INTEGER,
                home_team_name TEXT,
                away_team_id INTEGER,
                away_team_name TEXT,
                home_score INTEGER,
                away_score INTEGER,
                venue_id INTEGER,
                referee_id INTEGER,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        
        # 创建球队表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sportmonks_teams (
                team_id INTEGER PRIMARY KEY,
                name TEXT,
                short_name TEXT,
                logo TEXT,
                country TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        
        # 创建球员表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sportmonks_players (
                player_id INTEGER PRIMARY KEY,
                name TEXT,
                position TEXT,
                team_id INTEGER,
                nationality TEXT,
                birth_date TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        
        # 创建联赛表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sportmonks_leagues (
                league_id INTEGER PRIMARY KEY,
                name TEXT,
                country TEXT,
                season_id INTEGER,
                season_name TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        
        # 创建 xG 数据表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sportmonks_xg (
                match_id INTEGER PRIMARY KEY,
                home_xg REAL,
                away_xg REAL,
                home_xg_against REAL,
                away_xg_against REAL,
                source TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        
        # 创建赔率表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sportmonks_odds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                home_win REAL,
                draw REAL,
                away_win REAL,
                over_25 REAL,
                under_25 REAL,
                btts_yes REAL,
                btts_no REAL,
                ah_line REAL,
                ah_home_odds REAL,
                ah_away_odds REAL,
                bookmaker TEXT,
                timestamp TIMESTAMP,
                created_at TIMESTAMP
            )
        """)
        
        # 创建球队状态表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sportmonks_team_form (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER,
                match_id INTEGER,
                form_5 TEXT,
                form_10 TEXT,
                goals_for INTEGER,
                goals_against INTEGER,
                points INTEGER,
                created_at TIMESTAMP
            )
        """)
        
        # 创建交锋记录表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sportmonks_head_to_head (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                home_team_id INTEGER,
                away_team_id INTEGER,
                matches INTEGER,
                home_wins INTEGER,
                draws INTEGER,
                away_wins INTEGER,
                home_goals INTEGER,
                away_goals INTEGER,
                created_at TIMESTAMP
            )
        """)
        
        # 创建积分榜表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sportmonks_standings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER,
                team_id INTEGER,
                position INTEGER,
                points INTEGER,
                matches_played INTEGER,
                wins INTEGER,
                draws INTEGER,
                losses INTEGER,
                goals_for INTEGER,
                goals_against INTEGER,
                goal_difference INTEGER,
                season_id INTEGER,
                created_at TIMESTAMP
            )
        """)
        
        # 创建索引
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_date ON sportmonks_matches(date)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_league ON sportmonks_matches(league_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_home_team ON sportmonks_matches(home_team_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_away_team ON sportmonks_matches(away_team_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_odds_match ON sportmonks_odds(match_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_form_team ON sportmonks_team_form(team_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_form_match ON sportmonks_team_form(match_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_head_to_head_teams ON sportmonks_head_to_head(home_team_id, away_team_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_standings_league ON sportmonks_standings(league_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_standings_team ON sportmonks_standings(team_id)")

        # 迁移：为已存在的 sportmonks_odds 表追加 AH 列（幂等，列已存在时忽略）
        self._migrate_add_ah_columns()

        self.conn.commit()

    def _migrate_add_ah_columns(self):
        """
        迁移：向 sportmonks_odds 表追加亚盘字段（如果尚不存在）。
        使用 ALTER TABLE … ADD COLUMN，SQLite 已存在列时会抛出 OperationalError，
        此处静默忽略以保持幂等性。
        """
        for col, col_type in [
            ("ah_line", "REAL"),
            ("ah_home_odds", "REAL"),
            ("ah_away_odds", "REAL"),
        ]:
            try:
                self.cursor.execute(
                    f"ALTER TABLE sportmonks_odds ADD COLUMN {col} {col_type}"
                )
            except Exception:
                pass  # 列已存在，忽略
    
    def close(self):
        """
        关闭数据库连接
        """
        if self.conn:
            self.conn.close()
    
    def save_match(self, match: Match):
        """
        保存比赛数据
        
        Args:
            match: Match 对象
        """
        try:
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO sportmonks_matches 
                (match_id, date, time, status, league_id, league_name, 
                 home_team_id, home_team_name, away_team_id, away_team_name, 
                 home_score, away_score, venue_id, referee_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    match.match_id,
                    match.date,
                    match.time,
                    match.status,
                    match.league_id,
                    match.league_name,
                    match.home_team_id,
                    match.home_team_name,
                    match.away_team_id,
                    match.away_team_name,
                    match.home_score,
                    match.away_score,
                    match.venue_id,
                    match.referee_id,
                    match.created_at,
                    match.updated_at
                )
            )
        except Exception as e:
            print(f"Error saving match: {e}")
    
    def save_team(self, team: Team):
        """
        保存球队数据
        
        Args:
            team: Team 对象
        """
        try:
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO sportmonks_teams 
                (team_id, name, short_name, logo, country, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    team.team_id,
                    team.name,
                    team.short_name,
                    team.logo,
                    team.country,
                    team.created_at,
                    team.updated_at
                )
            )
        except Exception as e:
            print(f"Error saving team: {e}")
    
    def save_player(self, player: Player):
        """
        保存球员数据
        
        Args:
            player: Player 对象
        """
        try:
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO sportmonks_players 
                (player_id, name, position, team_id, nationality, birth_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    player.player_id,
                    player.name,
                    player.position,
                    player.team_id,
                    player.nationality,
                    player.birth_date,
                    player.created_at,
                    player.updated_at
                )
            )
        except Exception as e:
            print(f"Error saving player: {e}")
    
    def save_league(self, league: League):
        """
        保存联赛数据
        
        Args:
            league: League 对象
        """
        try:
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO sportmonks_leagues 
                (league_id, name, country, season_id, season_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    league.league_id,
                    league.name,
                    league.country,
                    league.season_id,
                    league.season_name,
                    league.created_at,
                    league.updated_at
                )
            )
        except Exception as e:
            print(f"Error saving league: {e}")
    
    def save_xg_data(self, xg_data: XGData):
        """
        保存 xG 数据
        
        Args:
            xg_data: XGData 对象
        """
        try:
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO sportmonks_xg 
                (match_id, home_xg, away_xg, home_xg_against, away_xg_against, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    xg_data.match_id,
                    xg_data.home_xg,
                    xg_data.away_xg,
                    xg_data.home_xg_against,
                    xg_data.away_xg_against,
                    xg_data.source,
                    xg_data.created_at,
                    xg_data.updated_at
                )
            )
        except Exception as e:
            print(f"Error saving xG data: {e}")
    
    def save_odds(self, odds: Odds):
        """
        保存赔率数据（含亚盘字段）

        Args:
            odds: Odds 对象
        """
        try:
            self.cursor.execute(
                """
                INSERT INTO sportmonks_odds
                (match_id, home_win, draw, away_win, over_25, under_25,
                 btts_yes, btts_no, ah_line, ah_home_odds, ah_away_odds,
                 bookmaker, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    odds.match_id,
                    odds.home_win,
                    odds.draw,
                    odds.away_win,
                    odds.over_25,
                    odds.under_25,
                    odds.btts_yes,
                    odds.btts_no,
                    odds.ah_line,
                    odds.ah_home_odds,
                    odds.ah_away_odds,
                    odds.bookmaker,
                    odds.timestamp,
                    odds.created_at,
                )
            )
        except Exception as e:
            print(f"Error saving odds: {e}")
    
    def save_team_form(self, team_form: TeamForm):
        """
        保存球队状态数据
        
        Args:
            team_form: TeamForm 对象
        """
        try:
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO sportmonks_team_form 
                (team_id, match_id, form_5, form_10, goals_for, goals_against, points, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    team_form.team_id,
                    team_form.match_id,
                    team_form.form_5,
                    team_form.form_10,
                    team_form.goals_for,
                    team_form.goals_against,
                    team_form.points,
                    team_form.created_at
                )
            )
        except Exception as e:
            print(f"Error saving team form: {e}")
    
    def save_head_to_head(self, h2h: HeadToHead):
        """
        保存交锋记录数据
        
        Args:
            h2h: HeadToHead 对象
        """
        try:
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO sportmonks_head_to_head 
                (home_team_id, away_team_id, matches, home_wins, draws, away_wins, home_goals, away_goals, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    h2h.home_team_id,
                    h2h.away_team_id,
                    h2h.matches,
                    h2h.home_wins,
                    h2h.draws,
                    h2h.away_wins,
                    h2h.home_goals,
                    h2h.away_goals,
                    h2h.created_at
                )
            )
        except Exception as e:
            print(f"Error saving head-to-head: {e}")
    
    def save_standings(self, standings: Standings):
        """
        保存积分榜数据
        
        Args:
            standings: Standings 对象
        """
        try:
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO sportmonks_standings 
                (league_id, team_id, position, points, matches_played, wins, draws, losses, goals_for, goals_against, goal_difference, season_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    standings.league_id,
                    standings.team_id,
                    standings.position,
                    standings.points,
                    standings.matches_played,
                    standings.wins,
                    standings.draws,
                    standings.losses,
                    standings.goals_for,
                    standings.goals_against,
                    standings.goal_difference,
                    standings.season_id,
                    standings.created_at
                )
            )
        except Exception as e:
            print(f"Error saving standings: {e}")
    
    def save_all_data(self, transformed_data: Dict[str, Any]):
        """
        保存所有转换后的数据
        
        Args:
            transformed_data: 转换后的数据字典
        """
        try:
            # 保存比赛数据
            for match in transformed_data.get('matches', []):
                self.save_match(match)
            
            # 保存球队数据
            for team in transformed_data.get('teams', []):
                self.save_team(team)
            
            # 保存球员数据
            for player in transformed_data.get('players', []):
                self.save_player(player)
            
            # 保存联赛数据
            for league in transformed_data.get('leagues', []):
                self.save_league(league)
            
            # 保存 xG 数据
            for xg_data in transformed_data.get('xg_data', []):
                self.save_xg_data(xg_data)
            
            # 保存赔率数据
            for odds in transformed_data.get('odds', []):
                self.save_odds(odds)
            
            # 保存球队状态数据
            for team_form in transformed_data.get('team_forms', []):
                self.save_team_form(team_form)
            
            # 保存交锋记录数据
            for h2h in transformed_data.get('head_to_head', []):
                self.save_head_to_head(h2h)
            
            # 保存积分榜数据
            for standings in transformed_data.get('standings', []):
                self.save_standings(standings)
            
            self.conn.commit()
            print(f"Saved {len(transformed_data.get('matches', []))} matches and related data")
        except Exception as e:
            print(f"Error saving all data: {e}")
            self.conn.rollback()
    
    # 数据查询方法
    def get_match(self, match_id: int) -> Dict[str, Any]:
        """
        获取单场比赛数据
        
        Args:
            match_id: 比赛 ID
            
        Returns:
            比赛数据字典
        """
        try:
            self.cursor.execute(
                "SELECT * FROM sportmonks_matches WHERE match_id = ?",
                (match_id,)
            )
            row = self.cursor.fetchone()
            if row:
                return {
                    'match_id': row[0],
                    'date': row[1],
                    'time': row[2],
                    'status': row[3],
                    'league_id': row[4],
                    'league_name': row[5],
                    'home_team_id': row[6],
                    'home_team_name': row[7],
                    'away_team_id': row[8],
                    'away_team_name': row[9],
                    'home_score': row[10],
                    'away_score': row[11],
                    'venue_id': row[12],
                    'referee_id': row[13],
                    'created_at': row[14],
                    'updated_at': row[15]
                }
            return None
        except Exception as e:
            print(f"Error getting match: {e}")
            return None
    
    def get_matches_by_date(self, date: str) -> List[Dict[str, Any]]:
        """
        获取指定日期的所有比赛
        
        Args:
            date: 日期字符串 (YYYY-MM-DD)
            
        Returns:
            比赛数据列表
        """
        try:
            self.cursor.execute(
                "SELECT * FROM sportmonks_matches WHERE date = ?",
                (date,)
            )
            rows = self.cursor.fetchall()
            matches = []
            for row in rows:
                matches.append({
                    'match_id': row[0],
                    'date': row[1],
                    'time': row[2],
                    'status': row[3],
                    'league_id': row[4],
                    'league_name': row[5],
                    'home_team_id': row[6],
                    'home_team_name': row[7],
                    'away_team_id': row[8],
                    'away_team_name': row[9],
                    'home_score': row[10],
                    'away_score': row[11],
                    'venue_id': row[12],
                    'referee_id': row[13],
                    'created_at': row[14],
                    'updated_at': row[15]
                })
            return matches
        except Exception as e:
            print(f"Error getting matches by date: {e}")
            return []
    
    def get_matches_by_league(self, league_id: int) -> List[Dict[str, Any]]:
        """
        获取指定联赛的所有比赛
        
        Args:
            league_id: 联赛 ID
            
        Returns:
            比赛数据列表
        """
        try:
            self.cursor.execute(
                "SELECT * FROM sportmonks_matches WHERE league_id = ?",
                (league_id,)
            )
            rows = self.cursor.fetchall()
            matches = []
            for row in rows:
                matches.append({
                    'match_id': row[0],
                    'date': row[1],
                    'time': row[2],
                    'status': row[3],
                    'league_id': row[4],
                    'league_name': row[5],
                    'home_team_id': row[6],
                    'home_team_name': row[7],
                    'away_team_id': row[8],
                    'away_team_name': row[9],
                    'home_score': row[10],
                    'away_score': row[11],
                    'venue_id': row[12],
                    'referee_id': row[13],
                    'created_at': row[14],
                    'updated_at': row[15]
                })
            return matches
        except Exception as e:
            print(f"Error getting matches by league: {e}")
            return []
    
    def get_team(self, team_id: int) -> Dict[str, Any]:
        """
        获取球队信息
        
        Args:
            team_id: 球队 ID
            
        Returns:
            球队数据字典
        """
        try:
            self.cursor.execute(
                "SELECT * FROM sportmonks_teams WHERE team_id = ?",
                (team_id,)
            )
            row = self.cursor.fetchone()
            if row:
                return {
                    'team_id': row[0],
                    'name': row[1],
                    'short_name': row[2],
                    'logo': row[3],
                    'country': row[4],
                    'created_at': row[5],
                    'updated_at': row[6]
                }
            return None
        except Exception as e:
            print(f"Error getting team: {e}")
            return None
    
    def get_team_form(self, team_id: int, match_id: int) -> Dict[str, Any]:
        """
        获取球队在指定比赛时的状态
        
        Args:
            team_id: 球队 ID
            match_id: 比赛 ID
            
        Returns:
            球队状态数据字典
        """
        try:
            self.cursor.execute(
                "SELECT * FROM sportmonks_team_form WHERE team_id = ? AND match_id = ?",
                (team_id, match_id)
            )
            row = self.cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'team_id': row[1],
                    'match_id': row[2],
                    'form_5': row[3],
                    'form_10': row[4],
                    'goals_for': row[5],
                    'goals_against': row[6],
                    'points': row[7],
                    'created_at': row[8]
                }
            return None
        except Exception as e:
            print(f"Error getting team form: {e}")
            return None
    
    def get_head_to_head(self, home_team_id: int, away_team_id: int) -> Dict[str, Any]:
        """
        获取两队交锋记录
        
        Args:
            home_team_id: 主队 ID
            away_team_id: 客队 ID
            
        Returns:
            交锋记录数据字典
        """
        try:
            self.cursor.execute(
                "SELECT * FROM sportmonks_head_to_head WHERE home_team_id = ? AND away_team_id = ?",
                (home_team_id, away_team_id)
            )
            row = self.cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'home_team_id': row[1],
                    'away_team_id': row[2],
                    'matches': row[3],
                    'home_wins': row[4],
                    'draws': row[5],
                    'away_wins': row[6],
                    'home_goals': row[7],
                    'away_goals': row[8],
                    'created_at': row[9]
                }
            return None
        except Exception as e:
            print(f"Error getting head-to-head: {e}")
            return None
    
    def get_standings(self, league_id: int) -> List[Dict[str, Any]]:
        """
        获取联赛积分榜
        
        Args:
            league_id: 联赛 ID
            
        Returns:
            积分榜数据列表
        """
        try:
            self.cursor.execute(
                "SELECT * FROM sportmonks_standings WHERE league_id = ? ORDER BY position",
                (league_id,)
            )
            rows = self.cursor.fetchall()
            standings = []
            for row in rows:
                standings.append({
                    'id': row[0],
                    'league_id': row[1],
                    'team_id': row[2],
                    'position': row[3],
                    'points': row[4],
                    'matches_played': row[5],
                    'wins': row[6],
                    'draws': row[7],
                    'losses': row[8],
                    'goals_for': row[9],
                    'goals_against': row[10],
                    'goal_difference': row[11],
                    'season_id': row[12],
                    'created_at': row[13]
                })
            return standings
        except Exception as e:
            print(f"Error getting standings: {e}")
            return []
    
    def get_xg_data(self, match_id: int) -> Dict[str, Any]:
        """
        获取比赛的 xG 数据
        
        Args:
            match_id: 比赛 ID
            
        Returns:
            xG 数据字典
        """
        try:
            self.cursor.execute(
                "SELECT * FROM sportmonks_xg WHERE match_id = ?",
                (match_id,)
            )
            row = self.cursor.fetchone()
            if row:
                return {
                    'match_id': row[0],
                    'home_xg': row[1],
                    'away_xg': row[2],
                    'home_xg_against': row[3],
                    'away_xg_against': row[4],
                    'source': row[5],
                    'created_at': row[6],
                    'updated_at': row[7]
                }
            return None
        except Exception as e:
            print(f"Error getting xG data: {e}")
            return None
    
    def get_odds(self, match_id: int) -> List[Dict[str, Any]]:
        """
        获取比赛的赔率数据
        
        Args:
            match_id: 比赛 ID
            
        Returns:
            赔率数据列表
        """
        try:
            self.cursor.execute(
                "SELECT * FROM sportmonks_odds WHERE match_id = ? ORDER BY timestamp DESC",
                (match_id,)
            )
            rows = self.cursor.fetchall()
            odds_list = []
            for row in rows:
                odds_list.append({
                    'id': row[0],
                    'match_id': row[1],
                    'home_win': row[2],
                    'draw': row[3],
                    'away_win': row[4],
                    'over_25': row[5],
                    'under_25': row[6],
                    'btts_yes': row[7],
                    'btts_no': row[8],
                    'ah_line': row[9],
                    'ah_home_odds': row[10],
                    'ah_away_odds': row[11],
                    'bookmaker': row[12],
                    'timestamp': row[13],
                    'created_at': row[14],
                })
            return odds_list
        except Exception as e:
            print(f"Error getting odds: {e}")
            return []
