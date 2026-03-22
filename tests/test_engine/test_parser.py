import pytest
from src.engine.parser import OutputParser


def test_extract_json_from_code_block():
    parser = OutputParser()
    text = '''
    Some text before
    ```json
    {"key": "value"}
    ```
    Some text after
    '''
    result = parser._extract_json(text)
    assert result == '{"key": "value"}'


def test_extract_json_plain():
    parser = OutputParser()
    text = '{"key": "value"}'
    result = parser._extract_json(text)
    assert result == '{"key": "value"}'


def test_validate_and_fix_missing_fields():
    parser = OutputParser()
    data = {
        "match_info": {"home_team": "A", "away_team": "B"},
        "model_output": {},
        "market": {},
        "decision": {"ev": 0.1, "confidence": 75},
    }

    result = parser._validate_and_fix(data)
    assert result is not None
    assert "final_probabilities" in result["model_output"]
    assert "confidence" in result["decision"]


def test_validate_probabilities_normalization():
    parser = OutputParser()
    data = {
        "match_info": {},
        "model_output": {
            "final_probabilities": {
                "home_win": "40%",
                "draw": "30%",
                "away_win": "20%"
            }
        },
        "market": {},
        "decision": {},
    }

    result = parser._validate_and_fix(data)
    probs = result["model_output"]["final_probabilities"]
    total = (
        float(probs["home_win"].replace("%", "")) +
        float(probs["draw"].replace("%", "")) +
        float(probs["away_win"].replace("%", ""))
    )
    assert 99 <= total <= 101
