import unittest
from nexus_sandbox.csf_transcript_ingest import segment_transcript_bounded
from nexus_sandbox.csf_extractive_proposals import propose_excerpts
from nexus_sandbox.csf_review_packet import prepare_review_packet
from nexus_sandbox.csf_v02 import CSFValidationError


class ReviewPacketTests(unittest.TestCase):
    def setUp(self):
        self.raw = "This synthetic statement is long enough to be extracted for independent review. " * 40
        self.bounded = segment_transcript_bounded("synthetic", self.raw, 300)
        self.extraction = propose_excerpts(self.raw, self.bounded)

    def test_source_context_and_provenance(self):
        packet = prepare_review_packet(self.raw, self.bounded, self.extraction)
        self.assertGreater(packet["review_item_count"], 0)
        self.assertFalse(packet["provider_called"])
        self.assertEqual(packet["external_writes"], 0)
        for item in packet["review_items"]:
            self.assertEqual(item["excerpt"], self.raw[item["start"]:item["end"]])
            self.assertIn(item["excerpt"], item["context"])
            self.assertEqual(item["status"], "pending_independent_review")
        self.assertEqual(packet, prepare_review_packet(self.raw, self.bounded, self.extraction))

    def test_tampering_fails_closed(self):
        with self.assertRaises(CSFValidationError):
            prepare_review_packet(self.raw + "tampered", self.bounded, self.extraction)
        self.extraction["proposals"][0]["start"] -= 1
        with self.assertRaises(CSFValidationError):
            prepare_review_packet(self.raw, self.bounded, self.extraction)

    def test_rejects_invalid_context_budget(self):
        with self.assertRaises(CSFValidationError):
            prepare_review_packet(self.raw, self.bounded, self.extraction, 0)


if __name__ == "__main__":
    unittest.main()
