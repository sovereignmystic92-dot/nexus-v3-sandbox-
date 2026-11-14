import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from module_evolution_recover_reconcile import recover_and_reconcile


class RecoverReconcileTests(unittest.TestCase):
    def setUp(self):
        payload = {"schema": "module_evolution_snapshot_v1", "receipts": []}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        self.digest = hashlib.sha256(canonical.encode()).hexdigest()
        self.checkpoint = json.dumps({"payload": payload, "sha256": self.digest}).encode()
        self.event = {
            "repository": "sovereignmystic92-dot/nexus-v3-sandbox-",
            "event": "workflow_run", "event_id": "44-1", "subject": "a" * 40,
            "source_url": "https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/44",
            "module_hints": []
        }
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / "next.json"

    def recovery(self, run_id, token):
        self.assertEqual((run_id, token), (42, "fixture"))
        return {
            "checkpoint": self.checkpoint,
            "provenance": {"run_id": 42, "head_sha": "a" * 40,
                           "verified_checkpoint_sha256": self.digest},
            "archive_sha256": "b" * 64, "archive_digest_verified": True
        }

    def test_reconciles_verified_checkpoint(self):
        result = recover_and_reconcile(42, "fixture", self.event, self.output, self.recovery)
        self.assertEqual(result["reconciliation"]["receipts"], 1)
        self.assertFalse(result["readiness_advanced"])
        self.assertFalse(result["cortex_persisted"])
        self.assertTrue(self.output.exists())

    def test_no_token_never_fetches(self):
        with self.assertRaises(ValueError):
            recover_and_reconcile(42, "", self.event, self.output,
                                  lambda *args: self.fail("network called"))

    def test_no_digest_fails_closed(self):
        def bad(*args):
            result = self.recovery(*args)
            result["archive_digest_verified"] = False
            return result
        with self.assertRaises(ValueError):
            recover_and_reconcile(42, "fixture", self.event, self.output, bad)
        self.assertFalse(self.output.exists())

    def test_wrong_run_provenance(self):
        def bad(*args):
            result = self.recovery(*args)
            result["provenance"]["run_id"] = 41
            return result
        with self.assertRaises(ValueError):
            recover_and_reconcile(42, "fixture", self.event, self.output, bad)

    def test_existing_destination_not_overwritten(self):
        self.output.write_text("existing")
        with self.assertRaises(ValueError):
            recover_and_reconcile(42, "fixture", self.event, self.output,
                                  lambda *args: self.fail("network called"))
        self.assertEqual(self.output.read_text(), "existing")


if __name__ == "__main__":
    unittest.main()
