"""Goalcast Sportmonks MCP 工具。"""

from __future__ import annotations

from typing import Any, Callable


def register_goalcast_sportmonks_tools(mcp: Any, service_factory: Callable[[], Any]) -> None:
    """注册 Sportmonks 数据源相关 MCP 工具。"""
    if service_factory is None:
        raise ValueError("service_factory is required")

    def _service() -> Any:
        return service_factory()

    @mcp.tool(
        description="读取指定日期（默认今天）的比赛列表，可按联赛过滤。"
    )
    async def goalcast_sportmonks_get_matches(
        date: str | None = None,
        leagues: list[str] | None = None,
    ) -> dict[str, Any]:
        """读取指定日期（默认今天）的比赛列表，可按联赛过滤。"""
        fixtures = await _service().get_matches(
            date=date,
            leagues=leagues,
        )
        data = _serialize(fixtures)
        return {
            "ok": True,
            "count": len(data),
            "data": data,
        }

    @mcp.tool(
        description="读取单场 Sportmonks 比赛详情（分析契约），仅需 fixture_id。"
    )
    async def goalcast_sportmonks_get_match(
        fixture_id: int,
        match_date: str | None = None,
    ) -> dict[str, Any]:
        """读取单场 Sportmonks 比赛详情（分析契约），仅需 fixture_id。"""
        payload = await _service().get_match_for_analysis(
            fixture_id=fixture_id,
            match_date=match_date,
        )
        return {
            "ok": True,
            "data": _serialize(payload),
        }


def _serialize(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value
