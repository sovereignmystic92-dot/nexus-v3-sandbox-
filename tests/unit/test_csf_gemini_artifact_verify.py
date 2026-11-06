"""Offline adversarial tests for Gemini review artifact integrity."""
import hashlib
import json
import unittest

from nexus_sandbox.csf_gemini_review_receipt import (
    HANDOFF_ID, PACKET, SOURCE_COMMIT, ReviewReceiptError,
)
from nexus_sandbox.csf_gemini_artifact_verify import verify_review_artifact


class GeminiArtifactTests(unittest.TestCase):
    def setUp(self):
        finding = {
            "finding_id": "SYNTHETIC-1", "severity": "medium",
            "source_path": "src/nexus_sandbox/csf_v02.py",
            "counterexample": "Synthetic source collision",
            "recommendation": "Preserve fail-closed behavior",
            "uncertainty": "Not authenticated Gemini output",
        }
        self.response = {
            "handoff_id": HANDOFF_ID, "source_commit": SOURCE_COMMIT,
            "findings": [finding], "disagreements": [],
        }
        self.artifact = json.dumps(self.response, sort_keys=True).encode()
        self.receipt = {
            "handoff_id": HANDOFF_ID, "source_commit": SOURCE_COMMIT,
            "payload_ref": PACKET, "agent": "Gemini-Independent-Analyst",
            "execution_run_url": "https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/12345",
            "response_artifact_sha256": hashlib.sha256(self.artifact).hexdigest(),
            "findings": [finding], "disagreements": [],
            "status": "REVIEW_SUBMITTED_UNVERIFIED",
        }

    def test_matching_artifact(self):
        self.assertTrue(verify_review_artifact(self.receipt, self.artifact))

    def test_modified_artifact_fails(self):
        with self.assertRaises(ReviewReceiptError):
            verify_review_artifact(self.receipt, self.artifact + b" ")

    def test_wrong_source_fails_even_with_updated_hash(self):
        altered = dict(self.response, source_commit="b" * 40)
        data = json.dumps(altered).encode()
        self.receipt["response_artifact_sha256"] = hashlib.sha256(data).hexdigest()
        with self.assertRaises(ReviewReceiptError):
            verify_review_artifact(self.receipt, data)

    def test_invalid_json_fails(self):
        data = b"{"
        self.receipt["response_artifact_sha256"] = hashlib.sha256(data).hexdigest()
        with self.assertRaises(ReviewReceiptError):
            verify_review_artifact(self.receipt, data)

    def test_oversized_artifact_fails(self):
        with self.assertRaises(ReviewReceiptError):
            verify_review_artifact(self.receipt, b"x" * 100001)


if __name__ == "__main__":
    unittest.main()
