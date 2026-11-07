"""Offline synthetic checkout binding tests without host Git dependency."""
import unittest

from nexus_sandbox.csf_gemini_handoff import HandoffError, require_exact_checkout


class GeminiCheckoutPreflightTests(unittest.TestCase):
    def test_matching_sha(self):
        self.assertTrue(require_exact_checkout("a" * 40, "a" * 40))

    def test_mismatched_sha_blocks(self):
        with self.assertRaises(HandoffError):
            require_exact_checkout("a" * 40, "b" * 40)

    def test_moving_ref_blocks(self):
        with self.assertRaises(HandoffError):
            require_exact_checkout("main", "a" * 40)


if __name__ == "__main__":
    unittest.main()
