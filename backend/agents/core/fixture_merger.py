from __future__ import annotations

from provider.models import ProviderFixture, UnifiedFixture
from utils.normalize import normalize_team_name


def _canonical_key(home: str, away: str, kickoff_unix: int) -> str:
    """构造合并用的规范化 key，时间取整到小时以容忍 ±1h 误差。"""
    return f"{normalize_team_name(home)}|{normalize_team_name(away)}|{kickoff_unix // 3600}"


def merge_fixtures(
    provider_fixtures: list[tuple[str, list[ProviderFixture]]],
) -> list[UnifiedFixture]:
    """
    将多个 provider 的 fixture 列表合并为统一的 UnifiedFixture 列表。

    Args:
        provider_fixtures: [(provider_name, fixtures), ...] 按优先级排列，
                           优先级高的 provider 的队名会被保留。

    Returns:
        list[UnifiedFixture]，每个元素的 provider_ids 包含所有匹配到的 provider ID。
    """
    unified: dict[str, UnifiedFixture] = {}

    for provider_name, fixtures in provider_fixtures:
        for pf in fixtures:
            key = _canonical_key(pf.home_team, pf.away_team, pf.kickoff_unix)
            if key in unified:
                unified[key].provider_ids[provider_name] = pf.fixture_id
            else:
                unified[key] = UnifiedFixture(
                    home_team=pf.home_team,
                    away_team=pf.away_team,
                    kickoff_unix=pf.kickoff_unix,
                    provider_ids={provider_name: pf.fixture_id},
                )

    return list(unified.values())
