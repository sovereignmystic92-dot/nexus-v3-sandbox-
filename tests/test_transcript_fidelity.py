import unittest
from nexus_sandbox.transcript_event_replay import replay_transcript_events
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
    def test_custom_chunk_size(self):
        raw = "🚀[music] " * 1500
        chunks = split_transcript(raw, 512)
        receipt = build_receipt(raw, 512)
        self.assertTrue(verify_readback(raw, chunks, receipt))
        self.assertFalse(verify_readback(raw, chunks, build_receipt(raw)))
    def test_receipt_chunk_size_tamper(self):
        raw = "abc" * 2000
        receipt = build_receipt(raw, 512)
        receipt["chunk_bytes"] = 1024
        self.assertFalse(verify_readback(raw, split_transcript(raw, 512), receipt))
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

class TranscriptReplayTests(unittest.TestCase):
    digest = "a" * 64

    def event(self, step, event_id=None, **overrides):
        value = {"event_id": event_id or step, "step": step,
                 "source_sha256": self.digest, "authorized": True, "evidence": True}
        value.update(overrides)
        return value

    def test_replay_full_and_idempotent(self):
        steps = ["source_verified", "archive_written", "archive_readback",
                 "derived_written", "derived_readback"]
        events = [self.event(step) for step in steps]
        result = replay_transcript_events(events + [dict(events[2])], self.digest)
        self.assertEqual(result["status"], "SYNTHETIC_COMPLETE")
        self.assertIsNone(result["next_step"])
        self.assertFalse(result["provider_writes"])
        self.assertFalse(result["audit_promotion"])

    def test_partial_failure_resumes_without_promotion(self):
        events = [self.event("source_verified"), self.event("archive_written")]
        result = replay_transcript_events(events, self.digest)
        self.assertEqual(result["next_step"], "archive_readback")
        self.assertEqual(result["status"], "SYNTHETIC_INCOMPLETE")
        self.assertFalse(result["audit_promotion"])

    def test_out_of_order_rejected(self):
        with self.assertRaises(ValueError):
            replay_transcript_events([self.event("archive_written")], self.digest)

    def test_conflicting_replay_rejected(self):
        event = self.event("source_verified")
        with self.assertRaises(ValueError):
            replay_transcript_events([event, dict(event, evidence=False)], self.digest)

    def test_unauthorized_and_unverified_rejected(self):
        for key in ("authorized", "evidence"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                replay_transcript_events([self.event("source_verified", **{key: False})], self.digest)

    def test_wrong_source_rejected(self):
        with self.assertRaises(ValueError):
            replay_transcript_events([self.event("source_verified", source_sha256="b"*64)], self.digest)


if __name__ == "__main__":
    unittest.main()
