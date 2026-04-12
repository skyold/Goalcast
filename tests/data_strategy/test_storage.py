import pytest
import tempfile
from pathlib import Path
from data_strategy.storage import AnalysisStorage


@pytest.fixture
def tmp_storage(tmp_path):
    return AnalysisStorage(db_path=tmp_path / "test.db", reports_dir=tmp_path / "reports")


def test_storage_creates_tables(tmp_storage):
    tmp_storage.init()
    # Should not raise
    tmp_storage.init()  # idempotent


def test_save_analysis_result(tmp_storage):
    tmp_storage.init()
    row_id = tmp_storage.save_analysis(
        match_date="2026-04-12",
        home_team="Arsenal",
        away_team="Chelsea",
        competition="Premier League",
        data_provider="sportmonks",
        model_version="v3.0",
        home_win_prob=0.52,
        draw_prob=0.25,
        away_win_prob=0.23,
        confidence=73,
        best_bet="home_win",
        ev_adjusted=0.09,
        result_json={"decision": {"bet_rating": "推荐"}},
    )
    assert row_id is not None


def test_save_creates_json_report(tmp_storage):
    tmp_storage.init()
    tmp_storage.save_analysis(
        match_date="2026-04-12",
        home_team="Arsenal",
        away_team="Chelsea",
        competition="Premier League",
        data_provider="footystats",
        model_version="v3.0",
        home_win_prob=0.49,
        draw_prob=0.27,
        away_win_prob=0.24,
        confidence=67,
        best_bet="home_win",
        ev_adjusted=0.06,
        result_json={"method": "v3.0"},
    )
    report_path = tmp_storage.reports_dir / "2026-04-12" / "Arsenal_vs_Chelsea_footystats_v30.json"
    assert report_path.exists()
