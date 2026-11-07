import os
import unittest
import urllib.error
from unittest.mock import patch

from nexus_sandbox.csf_v02 import CSFValidationError
from nexus_sandbox.csf_transcript_ingest import segment_transcript_bounded
from nexus_sandbox.csf_extractive_proposals import propose_excerpts
from nexus_sandbox.csf_review_packet import prepare_review_packet
from nexus_sandbox.csf_gemini_live_transport import review_with_gemini, GeminiReviewDiagnostic


class Response:
    status = 200
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, n):
        return self.data[:n]


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        raw = "Synthetic transcript statement that does not prove independent facts. " * 30
        bounded = segment_transcript_bounded("synthetic", raw, 300)
        self.packet = prepare_review_packet(raw, bounded, propose_excerpts(raw, bounded))

    def call(self, opener):
        with patch.dict(os.environ, {"GEMINI_API_KEY":"fake-key", "NEXUS_CSF_GEMINI_LIVE":"true"}):
            return review_with_gemini(self.packet, authorized=True, opener=opener)

    def test_unauthorized(self):
        with self.assertRaises(GeminiReviewDiagnostic) as raised:
            review_with_gemini(self.packet)
        self.assertEqual(raised.exception.category, "AUTHORIZATION_DISABLED")

    def test_http_error_is_redacted(self):
        def denied(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 429, "sensitive details", {}, None)
        with self.assertRaises(GeminiReviewDiagnostic) as raised:
            self.call(denied)
        self.assertEqual(raised.exception.category, "PROVIDER_QUOTA")
        self.assertNotIn("sensitive", str(raised.exception))

    def test_incomplete_and_invalid_contract_are_distinct(self):
        for raw, category in [
            (b'{"candidates":[{"finishReason":"MAX_TOKENS"}]}', "RESPONSE_NOT_FINISHED"),
            (b'{"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":"{}"}]}}]}',
             "RESPONSE_CONTRACT_MISMATCH"),
        ]:
            with self.subTest(category=category):
                with self.assertRaises(GeminiReviewDiagnostic) as raised:
                    self.call(lambda req, timeout: Response(raw))
                self.assertEqual(raised.exception.category, category)


if __name__ == "__main__":
    unittest.main()
