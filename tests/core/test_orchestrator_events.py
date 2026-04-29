import pytest
from unittest.mock import AsyncMock, MagicMock
from agents.core.orchestrator import Orchestrator
from agents.core.events import EventEmitter

@pytest.mark.asyncio
async def test_orchestrator_emits_events():
    adapter = MagicMock()
    emitter = EventEmitter()
    
    # Track emitted events
    emitted = []
    async def track(name, payload):
        emitted.append(name)
    emitter.subscribe(track)

    orch = Orchestrator(adapter, semi_mode=False, emitter=emitter)
    
    # Mock fetch to return 0 to end fast
    orch._fetch_and_prepare = AsyncMock(return_value=0)
    # Stop loops immediately
    orch.stop_event.set()
    
    await orch.run(leagues=["Premier League"], date="2026-04-29")
    
    # We expect 'pipeline_start' to be emitted at run, and 'pipeline_complete'
    assert "pipeline_start" in emitted
