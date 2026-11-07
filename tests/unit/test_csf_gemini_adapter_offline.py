import json
import unittest
from nexus_sandbox.csf_transcript_ingest import segment_transcript_bounded
from nexus_sandbox.csf_extractive_proposals import propose_excerpts
from nexus_sandbox.csf_review_packet import prepare_review_packet
from nexus_sandbox.csf_gemini_adapter_offline import build_gemini_review_request, parse_gemini_review_response
from nexus_sandbox.csf_v02 import CSFValidationError


class GeminiAdapterOfflineTests(unittest.TestCase):
    def setUp(self):
        raw = "This synthetic statement is long enough to extract for a contextual review. " * 30
        bounded = segment_transcript_bounded("synthetic", raw, 300)
        self.packet = prepare_review_packet(raw, bounded, propose_excerpts(raw, bounded))

    def test_bounded_request_and_strict_response(self):
        built = build_gemini_review_request(self.packet)
        self.assertFalse(built["provider_called"])
        self.assertEqual(built["external_writes"], 0)
        self.assertEqual(len(built["request"]["items"]), self.packet["review_item_count"])
        response = {"source_digest": self.packet["source_digest"], "reviews": [
            {"segment_id": item["segment_id"], "start": item["start"], "end": item["end"],
             "excerpt_sha256": item["excerpt_sha256"], "verdict": "insufficient_context",
             "rationale": "The transcript alone is not independent corroboration."}
            for item in self.packet["review_items"]]}
        result = parse_gemini_review_response(self.packet, json.dumps(response))
        self.assertFalse(result["factual_verification"])
        self.assertFalse(result["approved_for_persistence"])

    def test_malformed_and_oversized_fail_closed(self):
        with self.assertRaises(CSFValidationError):
            parse_gemini_review_response(self.packet, "not json")
        with self.assertRaises(CSFValidationError):
            parse_gemini_review_response(self.packet, "x" * 48001)
        self.packet["review_items"] *= 2
        with self.assertRaises(CSFValidationError):
            build_gemini_review_request(self.packet)


if __name__ == "__main__":
    unittest.main()
