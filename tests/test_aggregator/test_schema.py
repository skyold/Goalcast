import pytest
from src.aggregator.schema import (
    TeamStats,
    MatchInfo,
    OddsData,
    DataQuality,
    MatchType,
    DataQualityLevel,
    BetRating,
    AnalysisInput,
)


def test_team_stats_validation():
    stats = TeamStats(
        team_id="123",
        team_name="Test FC",
        xg_home=1.5,
        xg_away=1.2,
        xga_home=1.0,
        xga_away=1.3,
        ppg=1.8,
        recent_form=["W", "D", "L", "W", "W"],
        elo=1650.0,
        league_position=3,
    )

    assert stats.team_id == "123"
    assert stats.team_name == "Test FC"
    assert stats.xg_home == 1.5
    assert stats.elo == 1650.0


def test_odds_data_validation():
    odds = OddsData(
        opening_home=2.0,
        opening_draw=3.5,
        opening_away=4.0,
        current_home=1.95,
        current_draw=3.4,
        current_away=4.2,
    )

    assert odds.opening_home == 2.0
    assert odds.current_home == 1.95


def test_match_info():
    match = MatchInfo(
        match_id="456",
        home_team="Team A",
        away_team="Team B",
        competition="Premier League",
        match_type=MatchType.A,
        data_quality=DataQualityLevel.HIGH,
    )

    assert match.match_id == "456"
    assert match.home_team == "Team A"
    assert match.match_type == MatchType.A


def test_data_quality():
    dq = DataQuality(
        missing_fields=["injuries", "weather"],
        quality_level=DataQualityLevel.MEDIUM,
        confidence_penalty=10,
    )

    assert len(dq.missing_fields) == 2
    assert dq.quality_level == DataQualityLevel.MEDIUM
    assert dq.confidence_penalty == 10


def test_analysis_input():
    match_info = MatchInfo(
        match_id="789",
        home_team="Home FC",
        away_team="Away FC",
        competition="La Liga",
    )

    home_stats = TeamStats(
        team_id="1",
        team_name="Home FC",
        xg_home=1.5,
    )

    away_stats = TeamStats(
        team_id="2",
        team_name="Away FC",
        xg_away=1.2,
    )

    analysis_input = AnalysisInput(
        match_info=match_info,
        home_stats=home_stats,
        away_stats=away_stats,
    )

    assert analysis_input.match_info.home_team == "Home FC"
    assert analysis_input.home_stats.xg_home == 1.5
    assert analysis_input.away_stats.xg_away == 1.2
