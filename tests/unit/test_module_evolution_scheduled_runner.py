import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from module_evolution_scheduled_runner import recover_scheduled
from module_evolution_artifact_provenance import REPOSITORY, WORKFLOW


def run(run_id, when, status="completed", conclusion="success"):
    return {"id": run_id, "repository": {"full_name": REPOSITORY},
            "path": ".github/workflows/" + WORKFLOW, "head_branch": "main",
            "event": "schedule", "run_attempt": 1, "status": status,
            "conclusion": conclusion, "head_sha": "a" * 40, "created_at": when}


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.current = run(20, "2026-11-14T10:00:00Z", "in_progress", None)
        self.previous = run(19, "2026-11-13T10:00:00Z")
        self.event = {"repository": REPOSITORY, "event": "workflow_run",
                      "event_id": "20-1", "subject": "a" * 40,
                      "source_url": "https://github.com/" + REPOSITORY + "/actions/runs/20",
                      "module_hints": []}
        self.listing = {"total_count": 2, "workflow_runs": [self.current, self.previous]}

    def get(self, path, token):
        if path.endswith("/runs/20"):
            return self.current
        return self.listing

    def test_valid_predecessor_reconciles_without_activation(self):
        with TemporaryDirectory() as tmp:
            def recover(run_id, token, event, dest):
                self.assertEqual(run_id, 19)
                self.assertEqual(event, self.event)
                return {"source_run_id": 19, "archive_digest_verified": True,
                        "readiness_advanced": False, "cortex_persisted": False,
                        "reconciliation": {"new_receipts": 1, "previous_receipts": 1,
                                           "receipts": 2, "checkpoint_sha256": "b" * 64}}
            result = recover_scheduled(20, "token", self.event, Path(tmp) / "new.json",
                                       get=self.get, recover=recover)
            self.assertEqual(result["total_receipts"], 2)
            self.assertFalse(result["scheduled_recovery_enabled"])

    def test_missing_predecessor_rejects_before_recovery(self):
        self.listing = {"total_count": 1, "workflow_runs": [self.current]}
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "bootstrap"):
                recover_scheduled(20, "token", self.event, Path(tmp) / "new.json", get=self.get,
                                  recover=lambda *args: self.fail("must not recover"))

    def test_failed_predecessor_rejects(self):
        self.listing = {"total_count": 2, "workflow_runs": [self.current, dict(self.previous, conclusion="failure")]}
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "predecessor"):
                recover_scheduled(20, "token", self.event, Path(tmp) / "new.json", get=self.get,
                                  recover=lambda *args: self.fail("must not recover"))

    def test_rejects_event_sha_mismatch(self):
        self.event["subject"] = "b" * 40
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "source SHA mismatch"):
                recover_scheduled(20, "token", self.event, Path(tmp) / "new.json", get=self.get)

    def test_rejects_unverified_recovery(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "not authenticated"):
                recover_scheduled(20, "token", self.event, Path(tmp) / "new.json", get=self.get,
                                  recover=lambda *args: {"source_run_id": 19, "archive_digest_verified": False})


if __name__ == "__main__":
    unittest.main()
