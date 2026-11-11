import hashlib
import unittest
from nexus_sandbox.csf_transcription_adapter import validate_transcription
from nexus_sandbox.csf_v02 import CSFValidationError

S = [{"start_ms":0, "end_ms":1200, "text":"A colony ship travels between stars."},
     {"start_ms":1400, "end_ms":2400, "text":"Could someone steal it?"}]
PIN = hashlib.sha256("\n".join(s["text"] for s in S).encode()).hexdigest()

class TranscriptionAdapterTests(unittest.TestCase):
    def test_valid_offline_transcription(self):
        r = validate_transcription(S, document_id="test-audio", expected_sha256=PIN)
        self.assertEqual(r["transcription_segments"], 2)
        self.assertFalse(r["provider_called"])
        self.assertFalse(r["audio_verified"])
        self.assertEqual(r["external_writes"], 0)

    def test_rejects_overlap_and_mutation(self):
        for segments, pin in [(S, "0"*64),
                              ([S[0], dict(S[1], start_ms=500)], PIN),
                              ([dict(S[0], start_ms=True), S[1]], PIN)]:
            with self.assertRaises(CSFValidationError):
                validate_transcription(segments, document_id="test-audio", expected_sha256=pin)

if __name__ == "__main__":
    unittest.main()
