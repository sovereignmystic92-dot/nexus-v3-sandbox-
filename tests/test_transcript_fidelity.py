import unittest
from nexus_sandbox.transcript_fidelity import build_receipt, split_transcript, verify_readback


class TranscriptFidelityTests(unittest.TestCase):
    def test_preserves_unicode_and_cues(self):
        raw = "Ship — [music] 🌌\n\n" * 1000
        chunks = split_transcript(raw)
        self.assertEqual("".join(chunks), raw)
        self.assertTrue(verify_readback(raw, chunks, build_receipt(raw)))
    def test_whitespace_change_fails(self):
        raw = "A  B\n[music]"
        self.assertFalse(verify_readback(raw, [raw.replace("  ", " ")], build_receipt(raw)))
    def test_missing_chunk_fails(self):
        raw = "a" * 20000
        self.assertFalse(verify_readback(raw, split_transcript(raw)[:-1], build_receipt(raw)))
    def test_reordered_chunks_fail(self):
        raw = "a" * 12000 + "b" * 12000
        self.assertFalse(verify_readback(raw, list(reversed(split_transcript(raw))), build_receipt(raw)))
    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            split_transcript("")
    def test_chunk_bounds(self):
        with self.assertRaises(ValueError):
            split_transcript("abc", 100)
    def test_receipt_tamper_fails(self):
        raw = "hello"
        receipt = build_receipt(raw)
        receipt["sha256"] = "0" * 64
        self.assertFalse(verify_readback(raw, [raw], receipt))


if __name__ == "__main__":
    unittest.main()
