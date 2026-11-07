import json
import os
import unittest
from unittest.mock import patch

from nexus_sandbox.csf_v02 import CSFValidationError
from nexus_sandbox.csf_transcript_ingest import segment_transcript_bounded
from nexus_sandbox.csf_extractive_proposals import propose_excerpts
from nexus_sandbox.csf_review_packet import prepare_review_packet
from nexus_sandbox.csf_gemini_live_transport import review_with_gemini


class FakeResponse:
    status = 200

    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.data[:limit]


class GeminiLiveTransportTests(unittest.TestCase):
    def setUp(self):
        raw = "Synthetic statement in transcript context, not a proven fact. " * 30
        bounded = segment_transcript_bounded("synthetic", raw, 300)
        self.packet = prepare_review_packet(raw, bounded, propose_excerpts(raw, bounded))

    def test_disabled_without_two_explicit_gates(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key", "NEXUS_CSF_GEMINI_LIVE": "true"}):
            with self.assertRaises(CSFValidationError):
                review_with_gemini(self.packet)
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key", "NEXUS_CSF_GEMINI_LIVE": "false"}):
            with self.assertRaises(CSFValidationError):
                review_with_gemini(self.packet, authorized=True)

    def test_mock_response_never_promotes_or_persists(self):
        reviews = [{"segment_id": x["segment_id"], "start": x["start"], "end": x["end"],
                    "excerpt_sha256": x["excerpt_sha256"], "verdict": "insufficient_context",
                    "rationale": "Only transcript context was supplied."}
                   for x in self.packet["review_items"]]
        output = json.dumps({"source_digest": self.packet["source_digest"], "reviews": reviews})
        envelope = json.dumps({"candidates": [{"finishReason": "STOP",
            "content": {"parts": [{"text": output}]}}]}).encode()
        def fake_opener(request, timeout):
            self.assertEqual(request.full_url,
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent")
            self.assertEqual(timeout, 25)
            return FakeResponse(envelope)
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key", "NEXUS_CSF_GEMINI_LIVE": "true"}):
            result = review_with_gemini(self.packet, authorized=True, opener=fake_opener)
        self.assertTrue(result["provider_called"])
        self.assertFalse(result["factual_verification"])
        self.assertFalse(result["approved_for_persistence"])
        self.assertFalse(result["audit_gate_promoted"])
        self.assertEqual(result["external_writes"], 0)

    def test_malformed_provider_response_fails_closed(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key", "NEXUS_CSF_GEMINI_LIVE": "true"}):
            with self.assertRaises(CSFValidationError):
                review_with_gemini(self.packet, authorized=True,
                    opener=lambda req, timeout: FakeResponse(b'{"candidates":[]}'))


if __name__ == "__main__":
    unittest.main()
