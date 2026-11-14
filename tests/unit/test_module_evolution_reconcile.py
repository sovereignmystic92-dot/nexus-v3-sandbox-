"""Offline reconciliation guarantees: digest, replay, collision, and no promotion."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from module_evolution_runner import evaluate
from module_evolution_snapshot import save_snapshot
from module_evolution_reconcile import reconcile


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.previous = self.root / "previous.json"
        self.output = self.root / "next.json"
        self.event = {"repository": "sovereignmystic92-dot/nexus-v3-sandbox-",
                      "event": "workflow_run", "event_id": "run-1",
                      "subject": "a" * 40, "source_url": "https://github.com/example",
                      "module_hints": ["field_journal"]}
        db = self.root / "seed.sqlite"
        evaluate(db, self.event)
        self.digest = save_snapshot(db, self.previous)

    def test_new_receipt_and_replay(self):
        new = dict(self.event, event_id="run-2")
        result = reconcile(self.previous, new, self.output, self.digest)
        self.assertEqual(result["receipts"], 2)
        self.assertEqual(result["new_receipts"], 1)
        self.assertFalse(result["readiness_advanced"])
        self.assertFalse(result["transport_authenticated"])
        self.assertEqual(len(json.loads(self.output.read_text())["payload"]["receipts"]), 2)

    def test_idempotent_replay(self):
        result = reconcile(self.previous, self.event, self.output, self.digest)
        self.assertEqual(result["new_receipts"], 0)

    def test_untrusted_expected_digest_rejected(self):
        with self.assertRaises(ValueError):
            reconcile(self.previous, self.event, self.output, "0" * 64)
        self.assertFalse(self.output.exists())

    def test_tampered_snapshot_rejected(self):
        data = json.loads(self.previous.read_text())
        data["payload"]["receipts"][0]["status"] = "VERIFIED"
        self.previous.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            reconcile(self.previous, self.event, self.output, self.digest)
        self.assertFalse(self.output.exists())

    def test_conflicting_event_identity_rejected(self):
        altered = dict(self.event, source_url="https://github.com/changed")
        with self.assertRaises(ValueError):
            reconcile(self.previous, altered, self.output, self.digest)
        self.assertFalse(self.output.exists())

    def test_existing_output_rejected(self):
        self.output.write_text("keep")
        with self.assertRaises(ValueError):
            reconcile(self.previous, self.event, self.output, self.digest)
        self.assertEqual(self.output.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
