"""
数据策略层（Data Strategy Layer）

对外暴露的核心接口：
  - MatchContext：分析层的唯一数据契约
  - DataFusion：构建 MatchContext 的入口
  - get_understat_league_code：联赛代码映射工具

内部模块：
  - models.py   — 数据类型定义
  - quality.py  — 质量评估函数
  - resolver.py — DataResolver（fallback 链 + 缓存）
  - fusion.py   — DataFusion 引擎
"""

from datasource.datafusion.models import (
    MatchContext,
    TeamFormWindow,
    StandingsEntry,
    OddsSnapshot,
    XGStats,
    UNDERSTAT_LEAGUE_MAP,
    UNDERSTAT_SUPPORTED_LEAGUES,
    get_understat_league_code,
)
from datasource.datafusion.fusion import DataFusion
from datasource.datafusion.resolver import DataResolver

__all__ = [
    "MatchContext",
    "TeamFormWindow",
    "StandingsEntry",
    "OddsSnapshot",
    "XGStats",
    "UNDERSTAT_LEAGUE_MAP",
    "UNDERSTAT_SUPPORTED_LEAGUES",
    "get_understat_league_code",
    "DataFusion",
    "DataResolver",
]
