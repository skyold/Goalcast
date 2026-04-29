import json
import os
import tempfile
import unittest
from pathlib import Path

from agents.core.blackboard import load_partial, merge_update

class TestBlackboard(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = Path(self.temp_dir.name) / "test_mc.json"
        
        # Initial data
        self.initial_data = {
            "metadata": {"match_id": 123, "league": "Premier League"},
            "state": {"analyst": "pending"},
            "raw_data": {"sportmonks": {"some": "data"}}
        }
        with open(self.test_file, "w", encoding="utf-8") as f:
            json.dump(self.initial_data, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_partial(self):
        # Only load metadata and state
        loaded = load_partial(self.test_file, ["metadata", "state"])
        
        self.assertIn("metadata", loaded)
        self.assertIn("state", loaded)
        self.assertNotIn("raw_data", loaded)
        
        self.assertEqual(loaded["metadata"]["match_id"], 123)

    def test_merge_update_existing_keys(self):
        updates = {
            "state": {"analyst": "done", "trader": "pending"},
            "analysis": {"v4.0": {"win_rate": 0.6}}
        }
        merge_update(self.test_file, updates)
        
        with open(self.test_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Verify nested merge (state)
        self.assertEqual(data["state"]["analyst"], "done")
        self.assertEqual(data["state"]["trader"], "pending")
        
        # Verify new top-level key (analysis)
        self.assertIn("analysis", data)
        self.assertEqual(data["analysis"]["v4.0"]["win_rate"], 0.6)
        
        # Verify old data is preserved
        self.assertEqual(data["metadata"]["league"], "Premier League")

    def test_merge_update_new_file(self):
        new_file = Path(self.temp_dir.name) / "new_mc.json"
        updates = {"metadata": {"match_id": 456}}
        
        merge_update(new_file, updates)
        
        with open(new_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        self.assertEqual(data["metadata"]["match_id"], 456)

if __name__ == "__main__":
    unittest.main()
