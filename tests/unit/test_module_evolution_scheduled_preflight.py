import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from module_evolution_scheduled_preflight import scheduled_history_preflight
from module_evolution_artifact_provenance import REPOSITORY, WORKFLOW


def run(id, time, status="completed", conclusion="success"):
    return {"id": id, "repository": {"full_name": REPOSITORY},
            "path": ".github/workflows/" + WORKFLOW, "head_branch": "main",
            "event": "schedule", "run_attempt": 1, "status": status,
            "conclusion": conclusion, "created_at": time}


class ScheduledPreflightTests(unittest.TestCase):
    def setUp(self):
        self.current = run(20, "2026-11-14T10:00:00Z", "in_progress", None)
        self.previous = run(19, "2026-11-13T10:00:00Z")
        self.listing = {"total_count": 2, "workflow_runs": [self.current, self.previous]}

    def test_accepts_bounded_successful_predecessor_without_enabling(self):
        result = scheduled_history_preflight(self.current, self.listing, True)
        self.assertEqual(result["previous_run_id"], 19)
        self.assertFalse(result["scheduled_recovery_enabled"])
        self.assertFalse(result["bootstrap_authorized"])

    def test_rejects_missing_token(self):
        with self.assertRaises(ValueError):
            scheduled_history_preflight(self.current, self.listing, False)

    def test_rejects_empty_history_bootstrap(self):
        with self.assertRaisesRegex(ValueError, "bootstrap"):
            scheduled_history_preflight(self.current, {"total_count": 1, "workflow_runs": [self.current]}, True)

    def test_rejects_failed_immediate_predecessor(self):
        failed = dict(self.previous, conclusion="failure")
        with self.assertRaisesRegex(ValueError, "predecessor"):
            scheduled_history_preflight(self.current, {"total_count": 2, "workflow_runs": [self.current, failed]}, True)

    def test_rejects_truncated_listing(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            scheduled_history_preflight(self.current, {"total_count": 3, "workflow_runs": [self.current, self.previous]}, True)

    def test_rejects_rerun(self):
        with self.assertRaisesRegex(ValueError, "rerun"):
            scheduled_history_preflight(dict(self.current, run_attempt=2), self.listing, True)


if __name__ == "__main__":
    unittest.main()
