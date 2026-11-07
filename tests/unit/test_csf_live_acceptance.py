import unittest
from nexus_sandbox.csf_v02 import CSFValidationError
from nexus_sandbox.csf_live_acceptance import validate_live_acceptance_result, EXPECTED_SOURCE

GOOD = {
    "status": "GEMINI_CONTEXT_REVIEW_VALIDATED",
    "source_digest": EXPECTED_SOURCE,
    "review_count": 12,
    "provider_called": True,
    "external_writes": 0,
    "approved_for_persistence": False,
    "audit_gate_promoted": False,
    "external_corroboration": False,
    "factual_verification": False,
}
SHA = "a" * 40


class LiveAcceptanceTests(unittest.TestCase):
    def test_valid_context_only_receipt(self):
        receipt = validate_live_acceptance_result(GOOD, run_id=42426734429, commit_sha=SHA)
        self.assertEqual(receipt["status"], "ACCEPTED_CONTEXT_ONLY")
        self.assertFalse(receipt["audit_gate_promoted"])
        self.assertFalse(receipt["factual_verification"])
        self.assertEqual(receipt["review_count"], 12)

    def test_fail_closed_for_mutated_results(self):
        mutations = {
            "source_digest": "0" * 64,
            "review_count": 11,
            "provider_called": False,
            "external_writes": 1,
            "approved_for_persistence": True,
            "audit_gate_promoted": True,
            "external_corroboration": True,
            "factual_verification": True,
            "status": "UNKNOWN",
        }
        for key, value in mutations.items():
            with self.subTest(key=key):
                changed = dict(GOOD, **{key: value})
                with self.assertRaises(CSFValidationError):
                    validate_live_acceptance_result(changed, run_id=1, commit_sha=SHA)

    def test_missing_and_invalid_provenance(self):
        for run_id, sha in [(0, SHA), (True, SHA), (1, "not-a-sha")]:
            with self.assertRaises(CSFValidationError):
                validate_live_acceptance_result(GOOD, run_id=run_id, commit_sha=sha)
        with self.assertRaises(CSFValidationError):
            validate_live_acceptance_result({}, run_id=1, commit_sha=SHA)


if __name__ == "__main__":
    unittest.main()
