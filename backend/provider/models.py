from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProviderFixture:
    """单个 provider 返回的原始 fixture 信息。"""
    provider: str
    fixture_id: int
    home_team: str
    away_team: str
    kickoff_unix: int
    league_name: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class UnifiedFixture:
    """跨 provider 合并后的统一比赛对象。

    provider_ids: {"sportmonks": 18329, "oddalerts": 54201}
    某 provider 无对应比赛时该 key 不存在，用 .get("oddalerts") 安全取值。
    """
    home_team: str
    away_team: str
    kickoff_unix: int
    provider_ids: dict[str, int] = field(default_factory=dict)
