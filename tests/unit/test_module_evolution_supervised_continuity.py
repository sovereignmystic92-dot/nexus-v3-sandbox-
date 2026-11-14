import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from module_evolution_supervised_continuity import continue_history


class SupervisedContinuityTests(unittest.TestCase):
    def setUp(self):
        self.event = {"event": "workflow_run", "event_id": "42-1"}
        self.calls = []

    def discovery(self, run_id, token):
        self.calls.append("discovery")
        return {"current_run_id": 42, "previous_run_id": 41,
                "discovery_authenticated": True, "bootstrap_authorized": False}

    def recovery(self, run_id, token, event, destination):
        self.calls.append("recovery")
        return {"source_run_id": 41, "archive_digest_verified": True,
                "readiness_advanced": False, "cortex_persisted": False}

    def execute(self, discovery=None, recovery=None, event=None):
        with tempfile.TemporaryDirectory() as tmp:
            return continue_history(42, "test-token", self.event if event is None else event,
                                    Path(tmp) / "checkpoint.json",
                                    discovery or self.discovery, recovery or self.recovery)

    def test_composes_in_order(self):
        result = self.execute()
        self.assertEqual(self.calls, ["discovery", "recovery"])
        self.assertEqual(result["previous_run_id"], 41)
        self.assertFalse(result["unattended_enabled"])

    def test_rejects_untrusted_discovery(self):
        def bad(run_id, token):
            return {"current_run_id": 42, "previous_run_id": 41,
                    "discovery_authenticated": False, "bootstrap_authorized": False}
        with self.assertRaises(ValueError):
            self.execute(discovery=bad)
        self.assertEqual(self.calls, [])

    def test_rejects_implicit_bootstrap(self):
        def bad(run_id, token):
            return {"current_run_id": 42, "previous_run_id": 41,
                    "discovery_authenticated": True, "bootstrap_authorized": True}
        with self.assertRaises(ValueError):
            self.execute(discovery=bad)

    def test_rejects_predecessor_mismatch(self):
        def bad(run_id, token, event, destination):
            return {"source_run_id": 40, "archive_digest_verified": True,
                    "readiness_advanced": False, "cortex_persisted": False}
        with self.assertRaises(ValueError):
            self.execute(recovery=bad)

    def test_rejects_unverified_archive(self):
        def bad(run_id, token, event, destination):
            return {"source_run_id": 41, "archive_digest_verified": False,
                    "readiness_advanced": False, "cortex_persisted": False}
        with self.assertRaises(ValueError):
            self.execute(recovery=bad)

    def test_rejects_readiness_promotion(self):
        def bad(run_id, token, event, destination):
            return {"source_run_id": 41, "archive_digest_verified": True,
                    "readiness_advanced": True, "cortex_persisted": False}
        with self.assertRaises(ValueError):
            self.execute(recovery=bad)

    def test_rejects_unmatched_event(self):
        with self.assertRaises(ValueError):
            self.execute(event={"event": "workflow_run", "event_id": "99-1"})
        self.assertEqual(self.calls, [])

    def test_rejects_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "checkpoint.json"
            destination.write_text("existing")
            with self.assertRaises(ValueError):
                continue_history(42, "test-token", self.event, destination,
                                 self.discovery, self.recovery)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
