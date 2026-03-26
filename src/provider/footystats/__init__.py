"""
FootyStats API Provider

提供对 FootyStats API 所有 16 个端点的访问：
- 基础端点：联赛列表、国家列表、每日比赛
- 联赛数据：联赛统计、比赛、球队、球员、裁判、积分榜
- 详细数据：比赛详情、球队、球队近况、球员、裁判
- 统计数据：BTTS、Over 2.5
"""

from provider.footystats.client import FootyStatsProvider

# 导出主要类
__all__ = ["FootyStatsProvider"]

# 模块版本信息
__version__ = "2.0.0"
__author__ = "Goalcast Team"

# 便捷的工厂函数
def create_provider(api_key: str = "", **kwargs) -> FootyStatsProvider:
    """
    创建 FootyStats Provider 实例
    
    Args:
        api_key: API 密钥，不传则使用配置文件中的
        **kwargs: 其他配置参数
        
    Returns:
        FootyStatsProvider 实例
    """
    return FootyStatsProvider(api_key=api_key, **kwargs)
