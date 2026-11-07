"""Bounded segmentation must preserve exact source offsets and digest."""
import hashlib
import unittest
from nexus_sandbox.csf_transcript_ingest import segment_transcript_bounded
from nexus_sandbox.csf_v02 import CSFValidationError


class BoundedSegmentTests(unittest.TestCase):
    def test_roundtrip_and_stability(self):
        raw = ("A sentence with words.\\n" * 400) + "Tail."
        result = segment_transcript_bounded("source", raw, 300)
        spans = list(result["spans"].values())
        self.assertGreater(len(spans), 1)
        self.assertEqual(spans[0]["start"], 0)
        self.assertEqual(spans[-1]["end"], len(raw))
        self.assertEqual("".join(raw[s["start"]:s["end"]] for s in spans), raw)
        self.assertTrue(all(spans[i]["end"] == spans[i+1]["start"] for i in range(len(spans)-1)))
        self.assertTrue(all(hashlib.sha256(raw[s["start"]:s["end"]].encode()).hexdigest() == s["sha256"] for s in spans))
        self.assertEqual(result, segment_transcript_bounded("source", raw, 300))

    def test_invalid_bounds_fail_closed(self):
        for size in (True, 0, 255, 8193, "1000"):
            with self.assertRaises(CSFValidationError):
                segment_transcript_bounded("source", "A real sentence.", size)


if __name__ == "__main__":
    unittest.main()
