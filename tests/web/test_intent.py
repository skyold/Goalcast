import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from agents.web.intent import parse_intent

@pytest.mark.asyncio
async def test_parse_intent():
    mock_adapter = AsyncMock()
    mock_adapter.run_agent.return_value = SimpleNamespace(
        final_text='{"leagues": ["Premier League"], "date": "2026-04-29", "models": ["v4.0"]}'
    )
    
    result = await parse_intent("分析今天英超", mock_adapter)
    assert result["leagues"] == ["Premier League"]
    assert result["date"] == "2026-04-29"
    assert result["models"] == ["v4.0"]


@pytest.mark.asyncio
async def test_parse_intent_uses_today_context_and_normalizes_payload():
    mock_adapter = AsyncMock()
    mock_adapter.run_agent.return_value = SimpleNamespace(
        final_text='```json\n{"leagues": [1, "Premier League"], "date": "2026-04-29", "models": []}\n```'
    )

    result = await parse_intent("分析今天英超", mock_adapter)

    assert result == {
        "leagues": [1, "Premier League"],
        "date": "2026-04-29",
        "models": ["v4.0"],
    }

    called_prompt = mock_adapter.run_agent.await_args.args[1]
    assert "Today is " in called_prompt
    assert "If the request says today" in called_prompt
