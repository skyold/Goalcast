"""
Sportmonks API v3 Football Provider

提供对 Sportmonks API v3 核心端点的访问：
- 联赛与赛季：获取联赛列表、赛季详情
- 赛程与比赛：获取每日赛程、日期范围内的赛程、单场比赛详情、H2H 数据
- 积分榜：获取赛季积分榜
- 球队与球员：获取球队、球员的详细数据
- 预测数据：获取官方胜平负概率预测及价值投注建议 (Value Bets)
"""

from goalcast.provider.sportmonks.client import SportmonksProvider

# 导出主要类
__all__ = ["SportmonksProvider"]

# 模块版本信息
__version__ = "3.0.0"
__author__ = "Goalcast Team"

# 便捷的工厂函数
def create_provider(api_key: str = "", **kwargs) -> SportmonksProvider:
    """
    创建 Sportmonks Provider 实例
    
    Args:
        api_key: API 密钥，不传则使用配置文件中的
        **kwargs: 其他配置参数
        
    Returns:
        SportmonksProvider 实例
    """
    return SportmonksProvider(api_key=api_key, **kwargs)
