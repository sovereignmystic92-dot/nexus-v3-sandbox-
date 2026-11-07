"""Offline checks for the frozen Haiti source-candidate packet.

No API calls, claims promotion, or Cortex writes.
"""
import json
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "docs" / "csf" / "haiti-review-candidates-v0.1.json"


class HaitiPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = json.loads(PACKET.read_text(encoding="utf-8"))

    def test_digest_is_real_hex_and_source_id_present(self):
        src = self.packet["source"]
        self.assertRegex(src["sha256_utf8"], r"^[0-9a-f]{64}$")
        self.assertEqual(src["raw_segment_id"], "RAW-001")
        self.assertEqual(src["utf16_length"], 20152)
        self.assertFalse(src["audio_verified"])

    def test_all_candidates_are_bounded_source_claims(self):
        candidates = self.packet["candidates"]
        self.assertEqual(len(candidates), 5)
        self.assertEqual(len({c["id"] for c in candidates}), len(candidates))
        for candidate in candidates:
            self.assertEqual(candidate["source_segment"], "RAW-001")
            self.assertGreaterEqual(candidate["offset_utf16"], 0)
            self.assertLess(candidate["offset_utf16"], self.packet["source"]["utf16_length"])
            self.assertTrue(candidate["excerpt"].strip())
            self.assertEqual(candidate["verification_status"], "UNVERIFIED_SOURCE_CLAIM")
            self.assertEqual(candidate["confidence_level"], "unassessed")
            self.assertIn(candidate["claim_type"], ("observation", "inference", "scenario"))

    def test_no_promotion_to_validated_findings(self):
        self.assertEqual(self.packet["status"], "PRE_CSF_REVIEW_PACKET_NOT_VALIDATED_FINDINGS")
        self.assertNotIn("findings", self.packet)


if __name__ == "__main__":
    unittest.main()
