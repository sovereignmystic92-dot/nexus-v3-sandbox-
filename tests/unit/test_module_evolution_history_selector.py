import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from module_evolution_history_selector import select_previous, select_from_listing


def run(rid, when, conclusion="success", status="completed"):
    return {
        "id": rid, "created_at": when, "conclusion": conclusion,
        "status": status, "event": "schedule", "head_branch": "main",
        "repository": {"full_name": "sovereignmystic92-dot/nexus-v3-sandbox-"},
        "path": ".github/workflows/module-evolution-daily-observation.yml"
    }


class HistorySelectorTests(unittest.TestCase):
    NOW = "2026-11-14T13:00:00Z"

    def test_picks_immediate_predecessor(self):
        self.assertEqual(select_previous([run(10, "2026-11-13T13:00:00Z"),
                                          run(12, "2026-11-14T12:00:00Z")], 13, self.NOW), 12)

    def test_no_prior_run_is_explicit_bootstrap(self):
        self.assertIsNone(select_previous([], 13, self.NOW))

    def test_failed_predecessor_does_not_skip(self):
        with self.assertRaises(ValueError):
            select_previous([run(10, "2026-11-13T13:00:00Z"),
                             run(12, "2026-11-14T12:00:00Z", "failure")], 13, self.NOW)

    def test_in_progress_predecessor_does_not_skip(self):
        with self.assertRaises(ValueError):
            select_previous([run(12, "2026-11-14T12:00:00Z", None, "in_progress")], 13, self.NOW)

    def test_future_run_excluded(self):
        self.assertIsNone(select_previous([run(15, "2026-11-14T14:00:00Z")], 13, self.NOW))

    def test_rejects_partial_page(self):
        with self.assertRaises(ValueError):
            select_from_listing({"total_count": 2, "workflow_runs": [run(12, "2026-11-14T12:00:00Z")]}, 13, self.NOW)

    def test_rejects_duplicate(self):
        item = run(12, "2026-11-14T12:00:00Z")
        with self.assertRaises(ValueError):
            select_previous([item, item], 13, self.NOW)

    def test_rejects_wrong_repo(self):
        item = run(12, "2026-11-14T12:00:00Z")
        item["repository"]["full_name"] = "other/repo"
        with self.assertRaises(ValueError):
            select_previous([item], 13, self.NOW)

    def test_rejects_non_main_current(self):
        with self.assertRaises(ValueError):
            select_previous([], 13, self.NOW, "feature")

    def test_current_run_ignored(self):
        self.assertIsNone(select_previous([run(13, self.NOW)], 13, self.NOW))


if __name__ == "__main__":
    unittest.main()
