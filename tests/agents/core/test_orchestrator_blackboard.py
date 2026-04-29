import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from agents.core.orchestrator import Orchestrator

class TestOrchestratorBlackboard(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_and_prepare_blackboard(self):
        # Setup mock executor
        mock_executor = AsyncMock()
        mock_executor._tool_goalcast_sportmonks_get_matches.return_value = {
            "data": [
                {
                    "fixture_id": 999,
                    "home_team": "Team A",
                    "away_team": "Team B",
                    "league_name": "Test League"
                }
            ]
        }
        mock_executor._tool_goalcast_sportmonks_resolve_match.return_value = {
            "data": {"some_raw_data": 1}
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("agents.core.match_store.MATCHES_DIR", Path(temp_dir)), \
                 patch("agents.adapters.tool_executor.ToolExecutor", return_value=mock_executor), \
                 patch("agents.core.match_store.generate_match_id", return_value="test_mc_001"):
                 
                orchestrator = Orchestrator(adapter=None)
                # Overwrite _resolve_league_ids to bypass file reading
                orchestrator._resolve_league_ids = lambda x: [1]
                
                count = await orchestrator._fetch_and_prepare(leagues=["Test"], date="2026-04-28", models=["v4.0"])
                self.assertEqual(count, 1)
                
                # Check blackboard file
                expected_file = os.path.join(temp_dir, "test_mc_001.json")
                self.assertTrue(os.path.exists(expected_file))
                
                # Check blackboard file content
                with open(expected_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                # Because match_store.save overrides the file in the end!
                # the test file contains the merged record now!
                self.assertEqual(data["metadata"]["fixture_id"], 999)
                self.assertEqual(data["metadata"]["requested_models"], ["v4.0"])
                self.assertEqual(data["state"]["analyst"], "pending")
                self.assertIn("sportmonks", data["raw_data"])
                self.assertEqual(data["raw_data"]["sportmonks"]["some_raw_data"], 1)
                
                # legacy file is the same file as blackboard file
                self.assertEqual(data["status"], "pending")

if __name__ == "__main__":
    unittest.main()
