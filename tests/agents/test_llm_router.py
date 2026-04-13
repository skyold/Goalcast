import pytest
from agents.llm_router import generate_response

@pytest.mark.asyncio
async def test_generate_response(monkeypatch):
    async def mock_acompletion(*args, **kwargs):
        class MockMessage:
            content = "Mocked LLM Response"
        class MockChoice:
            message = MockMessage()
        class MockResponse:
            choices = [MockChoice()]
        return MockResponse()
        
    monkeypatch.setattr("agents.llm_router.acompletion", mock_acompletion)
    
    response = await generate_response("Test prompt", model="gpt-4o-mini")
    assert response == "Mocked LLM Response"
