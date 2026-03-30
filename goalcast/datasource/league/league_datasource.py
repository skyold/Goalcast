"""
联赛数据源

管理联赛和国家数据，提供联赛 - 国家映射缓存功能
"""

from typing import Dict, Optional, List
from goalcast.datasource.base import DataSource, DataCapability
from goalcast.datasource.types import DataSourceType, League
from goalcast.provider.base import BaseProvider
from goalcast.utils.logger import logger


class LeagueDataSource(DataSource[League]):
    """
    联赛数据源 - 管理联赛和国家数据
    
    主要功能：
    1. 获取联赛所属国家
    2. 缓存联赛 - 国家映射关系
    3. 提供联赛列表查询
    """
    
    def __init__(self, providers: List[BaseProvider] = None):
        """
        初始化联赛数据源
        
        Args:
            providers: Provider 列表，如果不传则使用默认配置
        """
        super().__init__(providers)
        # 联赛 - 国家映射缓存
        self._league_country_cache: Dict[str, str] = {}
        # 缓存是否已加载
        self._cache_loaded = False
        # 联赛数据缓存 TTL：24 小时
        self._cache_ttl_league: float = 86400.0
    
    @property
    def data_type(self) -> DataSourceType:
        """返回数据类型：LEAGUE"""
        return DataSourceType.LEAGUE
    
    def capabilities(self) -> DataCapability:
        """返回数据能力描述"""
        return DataCapability(
            type=DataSourceType.LEAGUE,
            name="联赛数据",
            description="联赛列表、国家映射等",
            providers=[p.name for p in self._providers],
            params={
                "league_name": "联赛名称",
            },
            update_freq=86400.0,  # 24 小时
            historical=True,
            realtime=False,
        )
    
    async def get_country(self, league_name: str) -> str:
        """
        获取联赛所属国家
        
        Args:
            league_name: 联赛名称
            
        Returns:
            国家名称，如果找不到则返回 "Unknown"
        """
        logger.debug(f"LeagueDataSource: get_country(league_name={league_name})")
        
        # 1. 检查缓存
        if league_name in self._league_country_cache:
            logger.debug(f"Cache hit for {league_name}")
            return self._league_country_cache[league_name]
        
        # 2. 加载联赛列表
        if not self._cache_loaded:
            await self._load_league_list()
        
        # 3. 返回结果
        country = self._league_country_cache.get(league_name, "Unknown")
        logger.debug(f"Country for {league_name}: {country}")
        return country
    
    async def _load_league_list(self):
        """
        从 Provider 加载联赛列表并构建缓存
        
        调用 Provider 的 get_league_list() 方法，
        解析返回数据并构建联赛 - 国家映射缓存
        """
        if self._cache_loaded:
            logger.debug("League list already loaded")
            return
        
        logger.debug("Loading league list from API...")
        
        try:
            # 调用 Provider
            raw_data = await self._try_providers("get_league_list")
            
            if not raw_data or not raw_data.get("success"):
                logger.warning("Failed to load league list from API")
                return
            
            # 解析数据
            data = raw_data.get("data", [])
            if not isinstance(data, list):
                logger.warning("Invalid league list data format")
                return
            
            # 构建缓存
            count = 0
            for league in data:
                league_name = league.get("name", "")
                country = league.get("country", "")
                
                if league_name and country:
                    self._league_country_cache[league_name] = country
                    count += 1
            
            self._cache_loaded = True
            logger.info(f"Loaded {count} leagues from API")
            
        except Exception as e:
            logger.error(f"Error loading league list: {e}")
            # 不抛出异常，避免影响调用方
    
    async def fetch(self, **params) -> Optional[League]:
        """
        获取联赛详情（可选实现）
        
        Args:
            **params: 查询参数，如 league_name, season_id 等
            
        Returns:
            League 对象，如果找不到则返回 None
        """
        league_name = params.get("league_name")
        if not league_name:
            logger.error("league_name is required")
            return None
        
        # 获取国家信息
        country = await self.get_country(league_name)
        
        # 创建 League 对象
        return League(
            league_id=league_name,  # 使用名称作为临时 ID
            name=league_name,
            country=country,
            season=params.get("season"),
            season_id=params.get("season_id"),
        )
    
    def parse(self, raw_data: Dict) -> Optional[League]:
        """
        解析原始数据为 League 对象
        
        Args:
            raw_data: 原始数据字典
            
        Returns:
            League 对象，如果解析失败则返回 None
        """
        if not raw_data:
            return None
        
        try:
            league_name = raw_data.get("name", "")
            country = raw_data.get("country", "")
            
            if not league_name:
                return None
            
            return League(
                league_id=raw_data.get("id", league_name),
                name=league_name,
                country=country or "Unknown",
                season=raw_data.get("season"),
                season_id=raw_data.get("season_id"),
            )
        except Exception as e:
            logger.error(f"Error parsing league data: {e}")
            return None
    
    async def refresh(self):
        """
        强制刷新联赛列表缓存
        
        清除现有缓存并重新从 API 加载
        """
        logger.info("Refreshing league list cache...")
        self._league_country_cache.clear()
        self._cache_loaded = False
        await self._load_league_list()
    
    def clear_cache(self):
        """清除所有缓存"""
        super().clear_cache()
        self._league_country_cache.clear()
        self._cache_loaded = False
        logger.debug("LeagueDataSource cache cleared")
