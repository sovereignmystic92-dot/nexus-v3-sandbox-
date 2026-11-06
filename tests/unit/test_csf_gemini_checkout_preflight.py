"""Offline synthetic checkout binding tests without host Git dependency."""
import unittest

from nexus_sandbox.csf_gemini_handoff import HandoffError


def require_exact_checkout(source_commit, observed_head):
    """Pure model of the CLI's fail-closed checkout SHA comparison."""
    import re
    if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise HandoffError("exact source SHA required")
    if observed_head != source_commit:
        raise HandoffError("checkout HEAD differs from requested source commit")
    return True


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
