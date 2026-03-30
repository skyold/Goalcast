from dataclasses import dataclass
from typing import Optional


@dataclass
class FullMatchData:
    """
    完整比赛数据

    聚合所有数据类别的数据，用于未来 ML 模型预测

    设计原则：
    - 组合而非继承
    - 保留各类数据的独立性
    - 为特征工程预留接口
    """
    match_id: int

    basic: Optional['MatchBasicData'] = None
    stats: Optional['MatchStatsData'] = None
    advanced: Optional['MatchAdvancedData'] = None
    odds: Optional['MatchOddsData'] = None
    teams: Optional['MatchTeamsData'] = None
    others: Optional['MatchOthersData'] = None

    features: dict = None
    prediction: dict = None

    def __post_init__(self):
        if self.features is None:
            self.features = {}
        if self.prediction is None:
            self.prediction = {}

    @property
    def is_complete(self) -> bool:
        """判断是否所有类别数据都已加载"""
        return all([
            self.basic is not None,
            self.stats is not None,
            self.advanced is not None,
            self.odds is not None,
            self.teams is not None,
        ])

    def to_feature_vector(self) -> dict:
        """
        转换为特征向量（未来 ML 使用）

        TODO: 实现特征工程逻辑
        """
        features = {}

        return features