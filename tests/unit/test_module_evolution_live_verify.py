import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from module_evolution_live_verify import verify_two_run_continuity

REPO = "sovereignmystic92-dot/nexus-v3-sandbox-"


class LiveVerificationTests(unittest.TestCase):
    def setUp(self):
        self.run = {
            "id": 42, "repository": {"full_name": REPO},
            "path": ".github/workflows/module-evolution-daily-observation.yml",
            "head_branch": "main", "status": "completed", "conclusion": "success",
            "run_attempt": 1, "event": "workflow_dispatch", "head_sha": "a" * 40,
        }
        self.calls = []

    def get(self, path, token):
        self.assertEqual(token, "test-token")
        self.assertTrue(path.endswith("/runs/42"))
        return self.run

    def continuity(self, rid, token, event, output):
        self.calls.append(event)
        return {"previous_run_id": 41, "recovery": {"reconciliation": {
            "previous_receipts": 1, "new_receipts": 1, "receipts": 2,
            "checkpoint_sha256": "b" * 64}}}

    def check(self):
        return verify_two_run_continuity(42, "test-token", "unused.json", self.get, self.continuity)

    def test_verified_run_event(self):
        result = self.check()
        self.assertEqual(result["total_receipts"], 2)
        self.assertEqual(self.calls[0]["event_id"], "42-1")
        self.assertEqual(self.calls[0]["subject"], "a" * 40)
        self.assertFalse(result["unattended_enabled"])

    def test_rejects_failed_run(self):
        self.run["conclusion"] = "failure"
        with self.assertRaises(ValueError):
            self.check()

    def test_rejects_rerun(self):
        self.run["run_attempt"] = 2
        with self.assertRaises(ValueError):
            self.check()

    def test_rejects_wrong_workflow(self):
        self.run["path"] = ".github/workflows/other.yml"
        with self.assertRaises(ValueError):
            self.check()

    def test_rejects_wrong_repository(self):
        self.run["repository"]["full_name"] = "other/repo"
        with self.assertRaises(ValueError):
            self.check()

    def test_rejects_missing_new_receipt(self):
        def unchanged(rid, token, event, output):
            return {"previous_run_id": 41, "recovery": {"reconciliation": {
                "previous_receipts": 1, "new_receipts": 0, "receipts": 1,
                "checkpoint_sha256": "b" * 64}}}
        with self.assertRaises(ValueError):
            verify_two_run_continuity(42, "test-token", "unused.json", self.get, unchanged)


if __name__ == "__main__":
    unittest.main()
