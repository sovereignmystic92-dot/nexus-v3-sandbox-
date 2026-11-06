"""Static contract tests for the manually dispatched CSF Gemini preparation job.

These are source-level checks, not GitHub-hosted dispatch or credential proofs.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/gemini-live-review-pilot.yml"


@unittest.skipUnless(WORKFLOW.is_file(), "workflow source unavailable in isolated test image")
class GeminiWorkflowCsfPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")
        cls.preparation = cls.source.split("\n  csf_prepare:\n", 1)[1]

    def test_manual_only_trigger(self):
        self.assertIn("workflow_dispatch:", self.source)
        self.assertNotIn("schedule:", self.source)
        self.assertNotIn("pull_request:", self.source)

    def test_no_credential_reference_in_preparation_job(self):
        self.assertNotIn("secrets.", self.preparation)
        self.assertNotIn("GEMINI_API_KEY", self.preparation)
        self.assertIn("persist-credentials: false", self.preparation)

    def test_prepare_is_main_only_and_requires_opt_in(self):
        self.assertIn("github.ref == 'refs/heads/main' && inputs.csf_prepare_only == true", self.preparation)
        self.assertIn("--include-review-request", self.preparation)
        self.assertIn("--source-commit", self.preparation)
        self.assertIn("actions/upload-artifact@v4", self.preparation)

    def test_existing_live_review_still_requires_free_tier_approval(self):
        live = self.source.split("\n  review:\n", 1)[1].split("\n  csf_prepare:\n", 1)[0]
        self.assertIn("inputs.free_tier_confirmed == true", live)
        self.assertIn("inputs.csf_prepare_only != true", live)
        self.assertIn("GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}", live)


if __name__ == "__main__":
    unittest.main()
