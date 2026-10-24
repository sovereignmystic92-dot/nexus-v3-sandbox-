import io
import json
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError

import smoke


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.env = {"GEMINI_API_KEY": "fake-unit-test-key", "GEMINI_FREE_TIER_CONFIRMED": "true"}
        self.opener = Mock()

    def response(self, data):
        self.opener.open.return_value = io.BytesIO(json.dumps(data).encode())

    def test_no_confirmation_or_key_never_calls_transport(self):
        for env in ({}, {"GEMINI_API_KEY": "fake"}, {"GEMINI_FREE_TIER_CONFIRMED": "true"}):
            with self.assertRaises(smoke.BridgeError):
                smoke.run(env, self.opener)
        self.opener.open.assert_not_called()

    def test_single_fixed_request_and_provisional_output(self):
        self.response({"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "Tuesday fits S1; S2 availability unconfirmed."}]}}]})
        result = smoke.run(self.env, self.opener)
        self.assertEqual(result["app_writes"], "NOT_ATTEMPTED")
        self.assertEqual(result["knowledge"], "PROPOSED")
        self.opener.open.assert_called_once()
        request = self.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, smoke.URL)
        self.assertNotIn(self.env["GEMINI_API_KEY"], request.full_url)
        payload = json.loads(request.data)
        self.assertNotIn("tools", payload)
        self.assertEqual(payload["generationConfig"]["maxOutputTokens"], 512)

    def test_timeout_and_http_error_no_retry_or_provider_body(self):
        for error in (TimeoutError("sensitive"), HTTPError(smoke.URL, 429, "sensitive", {}, None)):
            self.opener.reset_mock()
            self.opener.open.side_effect = error
            with self.assertRaises(smoke.BridgeError) as raised:
                smoke.run(self.env, self.opener)
            self.assertNotIn("sensitive", str(raised.exception))
            self.opener.open.assert_called_once()

    def test_blocked_truncated_tool_and_sensitive_responses_fail(self):
        for data in ({}, {"candidates": [{"finishReason": "MAX_TOKENS"}]},
                     {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"functionCall": {}}]}}]},
                     {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": self.env["GEMINI_API_KEY"]}]}}]}):
            self.response(data)
            with self.assertRaises(smoke.BridgeError):
                smoke.run(self.env, self.opener)

    def test_oversized_body_fails(self):
        self.opener.open.return_value = io.BytesIO(b" " * (smoke.MAX_RESPONSE_BYTES + 1))
        with self.assertRaisesRegex(smoke.BridgeError, "RESPONSE_TOO_LARGE"):
            smoke.run(self.env, self.opener)

    def test_redirect_refused(self):
        with self.assertRaisesRegex(smoke.BridgeError, "REDIRECT_REFUSED"):
            smoke.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.com")


if __name__ == "__main__":
    unittest.main()
