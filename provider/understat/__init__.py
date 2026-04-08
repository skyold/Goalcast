"""
Understat Provider

提供 Understat.com 的高级足球统计数据访问接口
"""

from .client import UnderstatProvider, create_provider

__all__ = ["UnderstatProvider", "create_provider"]
