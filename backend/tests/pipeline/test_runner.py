import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from provider.models import UnifiedFixture


def _make_unified(home: str, away: str, ts: int, sm_id: int, oa_id: int) -> UnifiedFixture:
    return UnifiedFixture(
        home_team=home, away_team=away, kickoff_unix=ts,
        provider_ids={"sportmonks": sm_id, "oddalerts": oa_id},
    )


@pytest.mark.asyncio
async def test_run_pipeline_collects_and_stores(tmp_path):
    unified = [_make_unified("Arsenal", "Chelsea", 1715000000, 100, 200)]

    with (
        patch("pipeline.runner.discover_fixtures", new=AsyncMock(return_value=unified)),
        patch("pipeline.runner.collect_match_data", new=AsyncMock(return_value={"oddalerts": {"_meta": {}}})),
        patch("pipeline.runner.match_store.MATCHES_DIR", tmp_path / "matches"),
        patch("pipeline.runner.match_store.exists_for_fixture", return_value=None),
        patch("pipeline.runner.registry.is_analyst_enabled", return_value=False),
    ):
        from pipeline.runner import run_pipeline
        result = await run_pipeline(leagues=[], dates=["2025-05-10"])

    assert result["discovered"] == 1
    assert result["collected"] == 1
    assert result["analyzed"] == 0


@pytest.mark.asyncio
async def test_run_pipeline_skips_existing_match(tmp_path):
    unified = [_make_unified("Arsenal", "Chelsea", 1715000000, 100, 200)]

    with (
        patch("pipeline.runner.discover_fixtures", new=AsyncMock(return_value=unified)),
        patch("pipeline.runner.match_store.MATCHES_DIR", tmp_path / "matches"),
        patch("pipeline.runner.match_store.exists_for_fixture", return_value="MC-EXISTING"),
        patch("pipeline.runner.match_store.get", return_value={"status": "collected"}),
        patch("pipeline.runner.registry.is_analyst_enabled", return_value=False),
    ):
        from pipeline.runner import run_pipeline
        result = await run_pipeline(leagues=[], dates=["2025-05-10"])

    assert result["collected"] == 0


@pytest.mark.asyncio
async def test_run_pipeline_calls_analyst_when_enabled(tmp_path):
    unified = [_make_unified("Arsenal", "Chelsea", 1715000000, 100, 200)]
    mock_analysis = {
        "home_xg": 1.5, "away_xg": 1.0,
        "ah_recommendation": "home", "confidence": 0.7,
        "kelly_fraction": 0.05, "analyzed_at": "2025-05-09T10:00:00+08:00",
    }

    with (
        patch("pipeline.runner.discover_fixtures", new=AsyncMock(return_value=unified)),
        patch("pipeline.runner.collect_match_data", new=AsyncMock(return_value={"oddalerts": {"_meta": {}}})),
        patch("pipeline.runner.match_store.MATCHES_DIR", tmp_path / "matches"),
        patch("pipeline.runner.match_store.exists_for_fixture", return_value=None),
        patch("pipeline.runner.registry.is_analyst_enabled", return_value=True),
        patch("pipeline.runner.run_analyst", new=AsyncMock(return_value=mock_analysis)),
    ):
        from pipeline.runner import run_pipeline
        result = await run_pipeline(leagues=[], dates=["2025-05-10"], adapter=MagicMock())

    assert result["analyzed"] == 1
