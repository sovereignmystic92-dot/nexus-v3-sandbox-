import unittest
from nexus_sandbox.github_cortex_event import normalize_run, REPOSITORY


def fixture():
    return dict(id=123, run_attempt=1, head_sha="a" * 40,
                conclusion="success", status="completed", workflow_id=55,
                repository={"full_name": REPOSITORY},
                html_url=f"https://github.com/{REPOSITORY}/actions/runs/123")


class GitHubCortexEnvelopeTests(unittest.TestCase):
    def test_stable_envelope(self):
        first = normalize_run(fixture())
        self.assertEqual(first, normalize_run(dict(reversed(list(fixture().items())))))
        self.assertEqual(first["event_key"], "github-run:123:attempt:1")
        self.assertEqual(len(first["digest_sha256"]), 64)

    def test_distinct_attempts(self):
        run = fixture()
        run["run_attempt"] = 2
        self.assertNotEqual(normalize_run(run)["event_key"], normalize_run(fixture())["event_key"])

    def test_incomplete_or_untrusted_run_holds(self):
        for field, value in (
            ("status", "in_progress"), ("conclusion", None),
            ("head_sha", "not-a-sha"), ("run_attempt", 0),
            ("id", True), ("workflow_id", None),
            ("html_url", "https://example.com/fake"),
            ("repository", {"full_name": "other/repo"}),
        ):
            with self.subTest(field=field):
                run = fixture()
                run[field] = value
                with self.assertRaises(ValueError):
                    normalize_run(run)

    def test_no_extra_metadata_leaks(self):
        run = fixture()
        run["secrets"] = "should-not-be-copied"
        run["actor"] = {"email": "private@example.com"}
        self.assertNotIn("private@example.com", str(normalize_run(run)))
        self.assertNotIn("should-not-be-copied", str(normalize_run(run)))


if __name__ == "__main__":
    unittest.main()
