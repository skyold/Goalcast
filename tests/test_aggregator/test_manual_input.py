import pytest
from src.aggregator.manual_input import parse_lineup, parse_injuries, parse_odds


def test_parse_lineup_simple():
    text = "Player A\nPlayer B\nPlayer C"
    result = parse_lineup(text)
    assert len(result) == 3
    assert "Player A" in result


def test_parse_lineup_with_numbers():
    text = "1. Goalkeeper\n2. Defender\n3. Midfielder"
    result = parse_lineup(text)
    assert len(result) == 3


def test_parse_lineup_empty():
    assert parse_lineup("") == []
    assert parse_lineup(None) == []


def test_parse_injuries():
    text = "Player A (out)\nPlayer B (doubtful)\nPlayer C"
    result = parse_injuries(text)
    assert len(result) == 3


def test_parse_odds():
    text = "home@2.10 draw@3.40 away@4.00"
    result = parse_odds(text)
    assert result is not None
    assert result.current_home == 2.10
    assert result.current_draw == 3.40
    assert result.current_away == 4.00


def test_parse_odds_empty():
    assert parse_odds("") is None
    assert parse_odds(None) is None
