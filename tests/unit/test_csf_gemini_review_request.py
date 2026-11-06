"""Adversarial offline Gemini request builder tests."""
from pathlib import Path
import tempfile
import unittest

from nexus_sandbox.csf_gemini_handoff import ALLOWED_PATHS, HandoffError, build_handoff
from nexus_sandbox.csf_gemini_review_request import build_review_request


class GeminiReviewRequestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ALLOWED_PATHS:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"synthetic":true}' if name.endswith(".json") else "# synthetic\n", encoding="utf-8")
        self.manifest = build_handoff(self.root, "a" * 40)

    def test_request_includes_full_sources_and_is_not_executed(self):
        request = build_review_request(self.root, self.manifest)
        self.assertEqual(request["status"], "REQUEST_PREPARED_NOT_EXECUTED")
        self.assertEqual([x["path"] for x in request["sources"]], list(ALLOWED_PATHS))
        self.assertIn("untrusted data", request["instructions"])

    def test_modified_source_fails(self):
        (self.root / ALLOWED_PATHS[2]).write_text("# changed\n")
        with self.assertRaises(HandoffError):
            build_review_request(self.root, self.manifest)

    def test_manifest_path_swap_fails(self):
        self.manifest["sources"][0]["path"] = ALLOWED_PATHS[1]
        with self.assertRaises(HandoffError):
            build_review_request(self.root, self.manifest)

    def test_incomplete_manifest_fails(self):
        self.manifest["sources"].pop()
        with self.assertRaises(HandoffError):
            build_review_request(self.root, self.manifest)

    def test_claimed_execution_fails(self):
        self.manifest["status"] = "GATE_C_PASSED"
        with self.assertRaises(HandoffError):
            build_review_request(self.root, self.manifest)


if __name__ == "__main__":
    unittest.main()
