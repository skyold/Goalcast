"""Sportmonks 工具函数模块"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class SportmonksUtils:
    """Sportmonks 工具类"""
    
    @staticmethod
    def parse_date(date_str: str) -> Optional[datetime]:
        """
        解析日期字符串
        
        Args:
            date_str: 日期字符串
            
        Returns:
            解析后的 datetime 对象
        """
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                return datetime.strptime(date_str, "%Y/%m/%d")
            except ValueError:
                return None
    
    @staticmethod
    def format_date(dt: datetime) -> str:
        """
        格式化日期为字符串
        
        Args:
            dt: datetime 对象
            
        Returns:
            格式化后的日期字符串 (YYYY-MM-DD)
        """
        return dt.strftime("%Y-%m-%d")
    
    @staticmethod
    def calculate_goal_difference(goals_for: int, goals_against: int) -> int:
        """
        计算净胜球
        
        Args:
            goals_for: 进球数
            goals_against: 失球数
            
        Returns:
            净胜球
        """
        return goals_for - goals_against
    
    @staticmethod
    def calculate_points(wins: int, draws: int) -> int:
        """
        计算积分
        
        Args:
            wins: 胜场数
            draws: 平局数
            
        Returns:
            积分
        """
        return wins * 3 + draws * 1
    
    @staticmethod
    def generate_form_string(matches: List[Dict[str, Any]], team_id: int) -> str:
        """
        生成球队状态字符串
        
        Args:
            matches: 比赛列表
            team_id: 球队 ID
            
        Returns:
            状态字符串，如 "WWDLW"
        """
        form = []
        for match in matches:
            home_team_id = match.get('localteam_id')
            away_team_id = match.get('visitorteam_id')
            home_score = match.get('localteam_score', 0)
            away_score = match.get('visitorteam_score', 0)
            
            if team_id == home_team_id:
                if home_score > away_score:
                    form.append('W')
                elif home_score == away_score:
                    form.append('D')
                else:
                    form.append('L')
            elif team_id == away_team_id:
                if away_score > home_score:
                    form.append('W')
                elif away_score == home_score:
                    form.append('D')
                else:
                    form.append('L')
        
        return ''.join(form)
    
    @staticmethod
    def filter_recent_matches(matches: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
        """
        过滤最近的比赛
        
        Args:
            matches: 比赛列表
            limit: 限制数量
            
        Returns:
            最近的比赛列表
        """
        # 按日期排序，最近的在前
        sorted_matches = sorted(
            matches, 
            key=lambda x: x.get('date', ''), 
            reverse=True
        )
        return sorted_matches[:limit]
    
    @staticmethod
    def validate_match_data(match_data: Dict[str, Any]) -> bool:
        """
        验证比赛数据的有效性
        
        Args:
            match_data: 比赛数据
            
        Returns:
            是否有效
        """
        required_fields = ['id', 'time', 'league', 'participants']
        for field in required_fields:
            if field not in match_data:
                return False
        
        # 验证时间数据
        time_data = match_data.get('time', {})
        if 'date' not in time_data or 'time' not in time_data:
            return False
        
        # 验证球队数据
        participants = match_data.get('participants', [])
        if len(participants) < 2:
            return False
        
        return True
    
    @staticmethod
    def extract_team_id(team_data: Dict[str, Any]) -> Optional[int]:
        """
        从球队数据中提取球队 ID
        
        Args:
            team_data: 球队数据
            
        Returns:
            球队 ID
        """
        return team_data.get('id') or team_data.get('team_id')
    
    @staticmethod
    def extract_league_id(league_data: Dict[str, Any]) -> Optional[int]:
        """
        从联赛数据中提取联赛 ID
        
        Args:
            league_data: 联赛数据
            
        Returns:
            联赛 ID
        """
        return league_data.get('id') or league_data.get('league_id')
    
    @staticmethod
    def safe_get(data: Dict[str, Any], keys: List[str], default=None) -> Any:
        """
        安全获取嵌套字典的值
        
        Args:
            data: 字典数据
            keys: 键列表
            default: 默认值
            
        Returns:
            获取的值或默认值
        """
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    @staticmethod
    def calculate_win_probability(odds: float) -> float:
        """
        根据赔率计算获胜概率
        
        Args:
            odds: 赔率
            
        Returns:
            概率 (0-1)
        """
        if odds <= 0:
            return 0.0
        return 1.0 / odds
    
    @staticmethod
    def calculate_overround(home_odds: float, draw_odds: float, away_odds: float) -> float:
        """
        计算超售率
        
        Args:
            home_odds: 主胜赔率
            draw_odds: 平局赔率
            away_odds: 客胜赔率
            
        Returns:
            超售率
        """
        if home_odds <= 0 or draw_odds <= 0 or away_odds <= 0:
            return 0.0
        return (1.0 / home_odds) + (1.0 / draw_odds) + (1.0 / away_odds)
    
    @staticmethod
    def normalize_probabilities(home_prob: float, draw_prob: float, away_prob: float) -> tuple:
        """
        标准化概率，使其和为 1
        
        Args:
            home_prob: 主胜概率
            draw_prob: 平局概率
            away_prob: 客胜概率
            
        Returns:
            标准化后的概率元组
        """
        total = home_prob + draw_prob + away_prob
        if total == 0:
            return (1/3, 1/3, 1/3)
        return (home_prob/total, draw_prob/total, away_prob/total)
