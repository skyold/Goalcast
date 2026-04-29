import pytest
from unittest.mock import AsyncMock
from agents.web.intent import parse_intent

@pytest.mark.asyncio
async def test_parse_intent():
    mock_adapter = AsyncMock()
    # Simulate LLM returning JSON string
    mock_adapter.run_agent.return_value = '{"leagues": ["Premier League"], "date": "2026-04-29", "models": ["v4.0"]}'
    
    result = await parse_intent("分析今天英超", mock_adapter)
    assert result["leagues"] == ["Premier League"]
    assert result["date"] == "2026-04-29"
