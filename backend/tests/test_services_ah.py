import pytest
from services.ah import derive_main_ah_line, parse_ah_outcome_line

def test_parse_home_minus_05():
    assert parse_ah_outcome_line("home_m05") == ("home", -0.5)

def test_parse_away_plus_075():
    assert parse_ah_outcome_line("away_p075") == ("away", 0.75)

def test_parse_away_plus_125():
    assert parse_ah_outcome_line("away_p125") == ("away", 1.25)

def test_parse_home_zero():
    assert parse_ah_outcome_line("home_0") == ("home", 0.0)

def test_parse_invalid():
    assert parse_ah_outcome_line("home") is None
    assert parse_ah_outcome_line("draw") is None

def test_derive_picks_closest_to_even():
    rows = [
        {"market_id": 51, "outcome": "home_m05",  "current": 2.30, "bookmaker_id": 1},
        {"market_id": 51, "outcome": "away_p05",  "current": 1.65, "bookmaker_id": 1},
        {"market_id": 51, "outcome": "home_m025", "current": 1.95, "bookmaker_id": 1},
        {"market_id": 51, "outcome": "away_p025", "current": 1.90, "bookmaker_id": 1},  # closest
    ]
    line, h, a = derive_main_ah_line(rows, bookmaker_id=1)
    assert line == -0.25
    assert h == 1.95 and a == 1.90

def test_derive_returns_none_when_no_data():
    assert derive_main_ah_line([], bookmaker_id=1) is None

def test_derive_skips_other_bookmakers():
    rows = [
        {"market_id": 51, "outcome": "home_m05", "current": 1.85, "bookmaker_id": 2},
        {"market_id": 51, "outcome": "away_p05", "current": 1.95, "bookmaker_id": 2},
    ]
    assert derive_main_ah_line(rows, bookmaker_id=1) is None
