import json
import tempfile
import unittest
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[2]

def load(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

evaluate = load("daily_test_runner", "tools/module_evolution_runner.py").evaluate
export_snapshot = load("daily_test_snapshot", "tools/module_evolution_snapshot.py").export_snapshot
summarize = load("daily_test_report", "tools/module_evolution_daily_report.py").summarize


class DailyReportTests(unittest.TestCase):
    def test_report_counts_observations_without_promoting_readiness(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "events.sqlite"
            for i, hints in enumerate((["skill_forge", "field_journal"], ["field_journal"], [])):
                evaluate(db, {
                    "repository": "sovereignmystic92-dot/nexus-v3-sandbox-",
                    "event": "issues", "event_id": str(i), "subject": str(i),
                    "source_url": "https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/298",
                    "module_hints": hints,
                })
            report = summarize(export_snapshot(db))
            self.assertEqual(report["receipt_count"], 3)
            self.assertEqual(report["module_pending_observations"]["field_journal"], 2)
            self.assertEqual(report["module_pending_observations"]["skill_forge"], 1)
            self.assertEqual(report["verified_advancements"], 0)
            self.assertFalse(report["readiness_advanced"])

    def test_rejects_unexpected_receipt_status(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "events.sqlite"
            evaluate(db, {
                "repository": "sovereignmystic92-dot/nexus-v3-sandbox-",
                "event": "issues", "event_id": "1", "subject": "1",
                "source_url": "https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/298",
                "module_hints": ["skill_forge"],
            })
            snapshot = export_snapshot(db)
            snapshot["payload"]["receipts"][0]["status"] = "VERIFIED"
            with self.assertRaisesRegex(ValueError, "unexpected receipt status"):
                summarize(snapshot)


if __name__ == "__main__":
    unittest.main()
