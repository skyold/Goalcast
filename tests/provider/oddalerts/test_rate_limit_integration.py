import pytest
from unittest.mock import AsyncMock, patch
from provider.oddalerts.client import OddAlertsProvider


@pytest.mark.asyncio
async def test_provider_respects_token_bucket():
    p = OddAlertsProvider(api_key="x", rate_capacity=2, rate_refill_per_sec=0.0)
    # Patch the lower-level `_request` so the bucket gate inside `_request_raw`
    # still executes. (Deviates from the original plan which patched
    # `_request_raw`, which would have bypassed the gate entirely.)
    with patch.object(p, "_request", AsyncMock(return_value={"data": []})):
        await p.get_competitions(page=1)
        await p.get_competitions(page=2)
        with pytest.raises(RuntimeError):
            await p.get_competitions(page=3)
