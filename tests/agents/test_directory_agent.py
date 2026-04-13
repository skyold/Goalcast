import pytest
from agents.core.directory_agent import DirectoryAgentLoader, DirectoryAgent
from agents.core.state import WorkflowState
import os

@pytest.fixture
def mock_role_dir(tmp_path):
    role_dir = tmp_path / "mock_role"
    role_dir.mkdir()
    (role_dir / "IDENTITY.md").write_text("I am a mock agent.")
    (role_dir / "tool-registry.jsonc").write_text('{"builtin": {"include": ["read"]}}')
    return str(role_dir)

def test_loader(mock_role_dir):
    config = DirectoryAgentLoader.load(mock_role_dir)
    assert "I am a mock agent." in config.system_prompt
    assert "read" in config.tools["builtin"]["include"]

@pytest.mark.asyncio
async def test_directory_agent(mock_role_dir, monkeypatch):
    async def mock_generate_response(prompt, model="gpt-4o-mini", system_prompt=None, tools=None):
        assert "mock agent" in system_prompt
        return "Processed"
        
    monkeypatch.setattr("agents.core.directory_agent.generate_response", mock_generate_response)
    
    agent = DirectoryAgent(name="test", role_dir=mock_role_dir)
    state = WorkflowState(task_id="1")
    new_state = await agent.execute(state)
    assert new_state.current_step == "test_DONE"