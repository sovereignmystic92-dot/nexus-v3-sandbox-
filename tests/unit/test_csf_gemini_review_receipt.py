"""Synthetic adversarial checks for Gemini CSF receipt binding."""
import unittest

from nexus_sandbox.csf_gemini_review_receipt import (
    ReviewReceiptError, verify_review_receipt, HANDOFF_ID, SOURCE_COMMIT, PACKET,
)


def receipt():
    return {
        "handoff_id": HANDOFF_ID,
        "source_commit": SOURCE_COMMIT,
        "payload_ref": PACKET,
        "agent": "Gemini-Independent-Analyst",
        "execution_run_url": "https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/12345",
        "response_artifact_sha256": "a" * 64,
        "findings": [{
            "finding_id": "SYNTHETIC-1", "severity": "medium",
            "source_path": "src/nexus_sandbox/csf_v02.py",
            "counterexample": "Synthetic collision between two source segments",
            "recommendation": "Preserve fail-closed collision behavior",
            "uncertainty": "Provider execution has not been authenticated",
        }],
        "disagreements": [],
        "status": "REVIEW_SUBMITTED_UNVERIFIED",
    }


class GeminiReceiptTests(unittest.TestCase):
    def test_valid_shape_does_not_claim_authentication(self):
        self.assertTrue(verify_review_receipt(receipt()))

    def test_stale_commit_fails(self):
        value = receipt()
        value["source_commit"] = "0" * 40
        with self.assertRaises(ReviewReceiptError):
            verify_review_receipt(value)

    def test_self_certification_fails(self):
        value = receipt()
        value["status"] = "GATE_C_PASSED"
        with self.assertRaises(ReviewReceiptError):
            verify_review_receipt(value)

    def test_missing_execution_reference_fails(self):
        value = receipt()
        value["execution_run_url"] = ""
        with self.assertRaises(ReviewReceiptError):
            verify_review_receipt(value)

    def test_no_findings_fails(self):
        value = receipt()
        value["findings"] = []
        with self.assertRaises(ReviewReceiptError):
            verify_review_receipt(value)

    def test_unexpected_fields_fail(self):
        value = receipt()
        value["cortex_write_authorized"] = True
        with self.assertRaises(ReviewReceiptError):
            verify_review_receipt(value)


if __name__ == "__main__":
    unittest.main()
