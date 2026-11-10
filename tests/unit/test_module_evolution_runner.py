"""Offline acceptance for bounded module event receipts."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("module_runner", ROOT / "tools/module_evolution_runner.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def event(**changes):
    base = dict(repository="sovereignmystic92-dot/nexus-v3-sandbox-",
                event="workflow_run", event_id="run-123", subject="sha123",
                source_url="https://github.com/example/run/123",
                module_hints=["skill_forge"])
    base.update(changes)
    return base

class ModuleEvolutionTests(unittest.TestCase):
    def test_duplicate_and_restart_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipts.db"
            first = module.evaluate(path, event())
            second = module.evaluate(path, event())
            self.assertEqual(first, second)
            self.assertEqual(first["status"], "PENDING_VALIDATION")
            self.assertFalse(first["readiness_advanced"])
            import sqlite3
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM event_receipts").fetchone()[0], 1)

    def test_noncontributing_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = module.evaluate(Path(tmp) / "receipts.db", event(module_hints=[]))
            self.assertEqual(result["modules"], [])
            self.assertFalse(result["readiness_advanced"])

    def test_reject_unknown_module_and_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipts.db"
            with self.assertRaises(ValueError):
                module.evaluate(path, event(module_hints=["root_access"]))
            with self.assertRaises(ValueError):
                module.evaluate(path, event(repository="someone/else"))

    def test_changed_payload_same_identity_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipts.db"
            module.evaluate(path, event())
            with self.assertRaises(ValueError):
                module.evaluate(path, event(module_hints=["trading_platform"]))

if __name__ == "__main__":
    unittest.main()
