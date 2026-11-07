import unittest
from nexus_sandbox.csf_transcript_ingest import segment_transcript_bounded
from nexus_sandbox.csf_extractive_proposals import propose_excerpts
from nexus_sandbox.csf_review_packet import prepare_review_packet
from nexus_sandbox.csf_independent_review_contract import validate_review_response
from nexus_sandbox.csf_v02 import CSFValidationError


class IndependentReviewContractTests(unittest.TestCase):
    def setUp(self):
        raw = "This synthetic statement is long enough to extract for a contextual review. " * 40
        segments = segment_transcript_bounded("synthetic", raw, 300)
        self.packet = prepare_review_packet(raw, segments, propose_excerpts(raw, segments))
        self.response = {"source_digest": self.packet["source_digest"], "reviews": [
            {"segment_id": x["segment_id"], "start": x["start"], "end": x["end"],
             "excerpt_sha256": x["excerpt_sha256"], "verdict": "insufficient_context",
             "rationale": "The transcript alone does not independently establish this claim."}
            for x in self.packet["review_items"]]}

    def test_complete_context_only_response(self):
        result = validate_review_response(self.packet, self.response)
        self.assertEqual(result["review_count"], len(self.packet["review_items"]))
        self.assertFalse(result["external_corroboration"])
        self.assertFalse(result["factual_verification"])
        self.assertFalse(result["approved_for_persistence"])
        self.assertFalse(result["audit_gate_promoted"])

    def test_missing_duplicate_and_tampered_reviews_fail(self):
        self.response["reviews"].pop()
        with self.assertRaises(CSFValidationError):
            validate_review_response(self.packet, self.response)
        self.response["reviews"].append(dict(self.response["reviews"][0]))
        with self.assertRaises(CSFValidationError):
            validate_review_response(self.packet, self.response)
        self.response["reviews"][-1]["excerpt_sha256"] = "0" * 64
        with self.assertRaises(CSFValidationError):
            validate_review_response(self.packet, self.response)

    def test_rejects_unexpected_verdict(self):
        self.response["reviews"][0]["verdict"] = "fact_checked_true"
        with self.assertRaises(CSFValidationError):
            validate_review_response(self.packet, self.response)


if __name__ == "__main__":
    unittest.main()
