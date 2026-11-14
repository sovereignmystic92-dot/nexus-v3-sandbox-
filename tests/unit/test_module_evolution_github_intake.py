import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("github_intake", ROOT / "tools/module_evolution_github_intake.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class GithubIntakeTests(unittest.TestCase):
    def test_issue_envelope_is_observation_only(self):
        envelope = module.normalize("issues", "delivery-123", {
            "repository": {"full_name": module.REPOSITORY},
            "issue": {"number": 298, "html_url": "https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/298"},
        })
        self.assertEqual(envelope["event_id"], "delivery-123")
        self.assertEqual(envelope["module_hints"], [])
        self.assertEqual(envelope["subject"], "298")

    def test_wrong_repository_rejected(self):
        with self.assertRaisesRegex(ValueError, "unexpected repository"):
            module.normalize("push", "delivery", {"repository": {"full_name": "other/repo"}, "after": "abc", "compare": "https://github.com/other/repo/compare/a...b"})

    def test_missing_provenance_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing trusted-shape provenance"):
            module.normalize("workflow_run", "delivery", {"repository": {"full_name": module.REPOSITORY}, "workflow_run": {"id": 123}})

    def test_unsupported_event_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported event"):
            module.normalize("deployment", "delivery", {})


if __name__ == "__main__":
    unittest.main()
