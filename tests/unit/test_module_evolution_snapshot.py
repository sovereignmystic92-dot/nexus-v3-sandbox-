"""Offline snapshot export/import acceptance, including separate DB readback."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


runner = load("runner_snapshot_test", "tools/module_evolution_runner.py")
snapshot = load("snapshot_test", "tools/module_evolution_snapshot.py")


def event(n):
    return {"repository": "sovereignmystic92-dot/nexus-v3-sandbox-",
            "event": "workflow_run", "event_id": str(n), "subject": "sha" + str(n),
            "source_url": "https://github.com/example/runs/" + str(n),
            "module_hints": ["skill_forge", "trading_platform"]}


class SnapshotTests(unittest.TestCase):
    def test_export_rehydrate_independent_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, dest = Path(tmp) / "first.sqlite", Path(tmp) / "second.sqlite"
            expected = [runner.evaluate(source, event(n)) for n in range(5)]
            path = Path(tmp) / "checkpoint.json"
            digest = snapshot.save_snapshot(source, path)
            self.assertEqual(snapshot.load_snapshot(dest, path), 5)
            self.assertEqual(snapshot.export_snapshot(dest)["sha256"], digest)
            self.assertEqual([runner.evaluate(dest, event(n)) for n in range(5)], expected)
            self.assertEqual(snapshot.load_snapshot(dest, path), 5)
            with sqlite3.connect(dest) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM event_receipts").fetchone()[0], 5)

    def test_tamper_rejected_before_database_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "src.sqlite", Path(tmp) / "dst.sqlite"
            runner.evaluate(src, event(1))
            value = snapshot.export_snapshot(src)
            value["payload"]["receipts"][0]["status"] = "VERIFIED"
            with self.assertRaises(ValueError):
                snapshot.import_snapshot(dst, value)
            self.assertFalse(dst.exists())

    def test_recomputed_digest_cannot_mask_changed_module_routing(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "src.sqlite", Path(tmp) / "dst.sqlite"
            runner.evaluate(src, event(1))
            value = snapshot.export_snapshot(src)
            value["payload"]["receipts"][0]["modules_json"] = '["field_journal"]'
            value["sha256"] = __import__("hashlib").sha256(
                snapshot.canonical(value["payload"]).encode()).hexdigest()
            with self.assertRaisesRegex(ValueError, "module hints and receipt disagree"):
                snapshot.import_snapshot(dst, value)
            self.assertFalse(dst.exists())

    def test_recomputed_digest_cannot_mask_missing_source_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "src.sqlite", Path(tmp) / "dst.sqlite"
            runner.evaluate(src, event(1))
            value = snapshot.export_snapshot(src)
            item = value["payload"]["receipts"][0]
            payload = json.loads(item["event_json"])
            payload["source_url"] = ""
            item["event_json"] = snapshot.canonical(payload)
            value["sha256"] = __import__("hashlib").sha256(
                snapshot.canonical(value["payload"]).encode()).hexdigest()
            with self.assertRaisesRegex(ValueError, "missing receipt provenance"):
                snapshot.import_snapshot(dst, value)
            self.assertFalse(dst.exists())

    def test_conflicting_existing_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "src.sqlite", Path(tmp) / "dst.sqlite"
            runner.evaluate(src, event(1))
            runner.evaluate(dst, event(1))
            with sqlite3.connect(dst) as db:
                db.execute("UPDATE event_receipts SET status='CORRUPTED'")
            with self.assertRaises(ValueError):
                snapshot.import_snapshot(dst, snapshot.export_snapshot(src))

    def test_duplicate_or_reordered_receipts_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "src.sqlite", Path(tmp) / "dst.sqlite"
            runner.evaluate(src, event(1))
            value = snapshot.export_snapshot(src)
            value["payload"]["receipts"].append(dict(value["payload"]["receipts"][0]))
            value["sha256"] = __import__("hashlib").sha256(snapshot.canonical(value["payload"]).encode()).hexdigest()
            with self.assertRaises(ValueError):
                snapshot.import_snapshot(dst, value)


if __name__ == "__main__":
    unittest.main()
