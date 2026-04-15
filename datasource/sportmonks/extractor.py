"""Sportmonks 数据提取模块"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any


class SportmonksExtractor:
    """Sportmonks 数据提取器"""
    
    def __init__(self, base_path: Path):
        """
        初始化提取器
        
        Args:
            base_path: 数据缓存基础路径
        """
        self.base_path = base_path
        self.db_path = base_path / "goalcast.db"
    
    def extract_matches_from_json(self, date: str) -> List[Dict[str, Any]]:
        """
        从 JSON 文件中提取比赛数据
        
        Args:
            date: 日期字符串 (YYYY-MM-DD)
            
        Returns:
            比赛数据列表
        """
        matches_path = self.base_path / date / "sportmonks" / "matches.json"
        if not matches_path.exists():
            return []
        
        with open(matches_path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    
    def extract_extended_data_from_json(self, date: str) -> Dict[str, Dict[str, Any]]:
        """
        从 JSON 文件中提取扩展数据
        
        Args:
            date: 日期字符串 (YYYY-MM-DD)
            
        Returns:
            扩展数据字典
        """
        extended_path = self.base_path / date / "sportmonks" / "extended_data.json"
        if not extended_path.exists():
            return {}
        
        with open(extended_path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    
    def extract_matches_from_db(self) -> List[Dict[str, Any]]:
        """
        从数据库中提取比赛数据
        
        Returns:
            比赛数据列表
        """
        if not self.db_path.exists():
            return []
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM raw_sportmonks_matches")
            rows = cursor.fetchall()
            
            matches = []
            for row in rows:
                match_data = json.loads(row['raw_data'])
                matches.append({
                    'id': row['match_id'],
                    'date': row['date'],
                    'league_id': row['league_id'],
                    'data': match_data
                })
            return matches
        finally:
            conn.close()
    
    def extract_xg_from_db(self) -> Dict[int, Dict[str, Any]]:
        """
        从数据库中提取 xG 数据
        
        Returns:
            xG 数据字典，key 为 match_id
        """
        if not self.db_path.exists():
            return {}
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM raw_sportmonks_xg")
            rows = cursor.fetchall()
            
            xg_data = {}
            for row in rows:
                xg_data[row['match_id']] = json.loads(row['raw_data'])
            return xg_data
        finally:
            conn.close()
    
    def extract_predictions_from_db(self) -> Dict[int, Dict[str, Any]]:
        """
        从数据库中提取预测数据
        
        Returns:
            预测数据字典，key 为 match_id
        """
        if not self.db_path.exists():
            return {}
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM raw_sportmonks_predictions")
            rows = cursor.fetchall()
            
            predictions = {}
            for row in rows:
                predictions[row['match_id']] = json.loads(row['raw_data'])
            return predictions
        finally:
            conn.close()
    
    def extract_head_to_head_from_db(self) -> Dict[int, Dict[str, Any]]:
        """
        从数据库中提取交锋记录数据
        
        Returns:
            交锋记录数据字典，key 为 match_id
        """
        if not self.db_path.exists():
            return {}
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM raw_sportmonks_head_to_head")
            rows = cursor.fetchall()
            
            head_to_head = {}
            for row in rows:
                head_to_head[row['match_id']] = {
                    'home_team_id': row['home_team_id'],
                    'away_team_id': row['away_team_id'],
                    'data': json.loads(row['raw_data'])
                }
            return head_to_head
        finally:
            conn.close()
    
    def extract_team_form_from_db(self) -> Dict[int, Dict[str, Any]]:
        """
        从数据库中提取球队状态数据
        
        Returns:
            球队状态数据字典，key 为 match_id
        """
        if not self.db_path.exists():
            return {}
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM raw_sportmonks_team_form")
            rows = cursor.fetchall()
            
            team_form = {}
            for row in rows:
                team_form[row['match_id']] = {
                    'home_team_id': row['home_team_id'],
                    'away_team_id': row['away_team_id'],
                    'home_form': json.loads(row['home_form']),
                    'away_form': json.loads(row['away_form'])
                }
            return team_form
        finally:
            conn.close()
    
    def extract_standings_from_db(self) -> Dict[int, Dict[str, Any]]:
        """
        从数据库中提取积分榜数据
        
        Returns:
            积分榜数据字典，key 为 match_id
        """
        if not self.db_path.exists():
            return {}
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM raw_sportmonks_standings")
            rows = cursor.fetchall()
            
            standings = {}
            for row in rows:
                standings[row['match_id']] = {
                    'league_id': row['league_id'],
                    'season_id': row['season_id'],
                    'data': json.loads(row['raw_data'])
                }
            return standings
        finally:
            conn.close()
    
    def extract_all_data(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        提取所有数据
        
        Args:
            date: 日期字符串 (YYYY-MM-DD)，如果为 None 则从数据库提取所有数据
            
        Returns:
            包含所有提取数据的字典
        """
        data = {
            'matches': [],
            'extended_data': {},
            'xg_data': {},
            'predictions': {},
            'head_to_head': {},
            'team_form': {},
            'standings': {}
        }
        
        if date:
            # 从 JSON 文件提取指定日期的数据
            data['matches'] = self.extract_matches_from_json(date)
            data['extended_data'] = self.extract_extended_data_from_json(date)
        else:
            # 从数据库提取所有数据
            data['matches'] = self.extract_matches_from_db()
            data['xg_data'] = self.extract_xg_from_db()
            data['predictions'] = self.extract_predictions_from_db()
            data['head_to_head'] = self.extract_head_to_head_from_db()
            data['team_form'] = self.extract_team_form_from_db()
            data['standings'] = self.extract_standings_from_db()
        
        return data
