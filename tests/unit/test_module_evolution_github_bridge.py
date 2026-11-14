import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("nexus_github_bridge", ROOT / "tools/module_evolution_github_bridge.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class GithubBridgeTests(unittest.TestCase):
    def test_event_checkpoint_replay_is_stable(self):
        payload = {
            "repository": {"full_name": "sovereignmystic92-dot/nexus-v3-sandbox-"},
            "issue": {"number": 298, "html_url": "https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/298"},
        }
        with tempfile.TemporaryDirectory() as temp:
            db, checkpoint = Path(temp) / "events.sqlite", Path(temp) / "checkpoint.json"
            first = bridge.process(db, "issues", "delivery-1", payload, checkpoint)
            second = bridge.process(db, "issues", "delivery-1", payload, checkpoint)
            self.assertEqual(first["checkpoint_sha256"], second["checkpoint_sha256"])
            self.assertFalse(second["readiness_advanced"])
            self.assertEqual(second["receipt"]["status"], "PENDING_VALIDATION")
            self.assertEqual(len(json.loads(checkpoint.read_text())["payload"]["receipts"]), 1)
            with tempfile.TemporaryDirectory() as restore:
                self.assertEqual(bridge.snapshot.import_snapshot(Path(restore) / "restored.sqlite", json.loads(checkpoint.read_text())), 1)

    def test_reused_delivery_with_changed_event_is_rejected(self):
        payload = {
            "repository": {"full_name": "sovereignmystic92-dot/nexus-v3-sandbox-"},
            "issue": {"number": 298, "html_url": "https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/298"},
        }
        with tempfile.TemporaryDirectory() as temp:
            db, checkpoint = Path(temp) / "events.sqlite", Path(temp) / "checkpoint.json"
            bridge.process(db, "issues", "delivery-1", payload, checkpoint)
            changed = {**payload, "issue": {**payload["issue"], "html_url": "https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/299"}}
            with self.assertRaisesRegex(ValueError, "changed payload"):
                bridge.process(db, "issues", "delivery-1", changed, checkpoint)


if __name__ == "__main__":
    unittest.main()
