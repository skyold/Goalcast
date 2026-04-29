import asyncio
import pytest
from agents.core.events import EventEmitter

@pytest.mark.asyncio
async def test_event_emitter_subscribe_and_emit():
    emitter = EventEmitter()
    received = []

    async def callback(event_name: str, payload: dict):
        received.append((event_name, payload))

    emitter.subscribe(callback)
    
    await emitter.emit("test_event", {"key": "value"})
    
    # Allow event loop to process
    await asyncio.sleep(0.01)
    
    assert len(received) == 1
    assert received[0][0] == "test_event"
    assert received[0][1] == {"key": "value"}
