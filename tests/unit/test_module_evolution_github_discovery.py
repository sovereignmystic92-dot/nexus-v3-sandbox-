import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from module_evolution_github_discovery import discover_previous

REPO = "sovereignmystic92-dot/nexus-v3-sandbox-"
PATH = ".github/workflows/module-evolution-daily-observation.yml"


def run(rid, when, status="completed", conclusion="success"):
    return {"id": rid, "created_at": when, "status": status,
            "conclusion": conclusion, "event": "workflow_dispatch",
            "head_branch": "main", "path": PATH,
            "repository": {"full_name": REPO}}


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.current = run(30, "2026-11-14T13:00:00Z")
        self.previous = run(29, "2026-11-13T13:00:00Z")

    def fetch(self, path, token):
        self.assertEqual(token, "test-token")
        if path.endswith("/runs/30"):
            return self.current
        if "per_page=100&branch=main" in path:
            return {"total_count": 2, "workflow_runs": [self.current, self.previous]}
        raise AssertionError(path)

    def test_selects_authenticated_predecessor(self):
        result = discover_previous(30, "test-token", self.fetch)
        self.assertEqual(result["previous_run_id"], 29)
        self.assertFalse(result["bootstrap_authorized"])

    def test_requires_token(self):
        with self.assertRaises(ValueError):
            discover_previous(30, "", self.fetch)

    def test_rejects_mismatched_current_run(self):
        self.current["id"] = 31
        with self.assertRaises(ValueError):
            discover_previous(30, "test-token", self.fetch)

    def test_rejects_wrong_current_workflow(self):
        self.current["path"] = ".github/workflows/other.yml"
        with self.assertRaises(ValueError):
            discover_previous(30, "test-token", self.fetch)

    def test_rejects_truncated_listing(self):
        def truncated(path, token):
            if path.endswith("/runs/30"):
                return self.current
            return {"total_count": 3, "workflow_runs": [self.current, self.previous]}
        with self.assertRaises(ValueError):
            discover_previous(30, "test-token", truncated)

    def test_rejects_over_100_without_pagination(self):
        def oversized(path, token):
            if path.endswith("/runs/30"):
                return self.current
            return {"total_count": 101, "workflow_runs": []}
        with self.assertRaises(ValueError):
            discover_previous(30, "test-token", oversized)

    def test_no_implicit_bootstrap(self):
        def empty(path, token):
            if path.endswith("/runs/30"):
                return self.current
            return {"total_count": 1, "workflow_runs": [self.current]}
        with self.assertRaises(ValueError):
            discover_previous(30, "test-token", empty)

    def test_failed_predecessor_is_not_skipped(self):
        self.previous["conclusion"] = "failure"
        with self.assertRaises(ValueError):
            discover_previous(30, "test-token", self.fetch)


if __name__ == "__main__":
    unittest.main()
