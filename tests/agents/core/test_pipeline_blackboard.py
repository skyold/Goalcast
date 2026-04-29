import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from agents.core.pipeline import MatchPipeline

class TestPipelineAnalystBlackboard(unittest.IsolatedAsyncioTestCase):
    async def test_run_analyst_step_blackboard(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            match_id = "MC-TEST-001"
            filepath = temp_path / f"{match_id}.json"
            
            # Setup blackboard file
            initial_data = {
                "metadata": {
                    "match_id": match_id,
                    "requested_models": ["v4.0"]
                },
                "state": {
                    "analyst": "pending"
                },
                "raw_data": {
                    "sportmonks": {"some": "data"}
                }
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)
            
            # Setup mock adapter
            mock_adapter = AsyncMock()
            mock_result = AsyncMock()
            mock_result.final_text = '{"home_xg": 1.5, "ah_recommendation": "home"}'
            mock_adapter.run_agent.return_value = mock_result
            
            with patch("agents.core.match_store.MATCHES_DIR", temp_path), \
                 patch("agents.core.match_store.append_layer", return_value=None), \
                 patch("agents.core.match_store.update_status", return_value=None):
                
                pipeline = MatchPipeline(adapter=mock_adapter)
                
                # Run the step
                record = {"match_id": match_id}
                result = await pipeline.run_analyst_step(record)
                
                # Check results
                self.assertIn("v4.0", result)
                self.assertEqual(result["v4.0"]["home_xg"], 1.5)
                
                # Check blackboard updates
                with open(filepath, "r", encoding="utf-8") as f:
                    updated_data = json.load(f)
                    
                self.assertEqual(updated_data["state"]["analyst"], "done")
                self.assertIn("v4.0", updated_data["analysis"])
                self.assertEqual(updated_data["analysis"]["v4.0"]["ah_recommendation"], "home")

if __name__ == "__main__":
    unittest.main()
