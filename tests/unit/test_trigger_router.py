"""Synthetic-only tests; no provider, workflow, or account-wide hooks."""
import unittest

from nexus_sandbox.trigger_router import classify


class TriggerRouterTests(unittest.TestCase):
    def route(self, message, **kwargs):
        return classify(message, trusted_user_turn=True, **kwargs)

    def test_normal_chat_remains_normal(self):
        for message in ("What's for dinner?", "Explain Nexus", "Summarize this video",
                        "Please nexus process this", "The phrase nexus archive appears here",
                        '"nexus process this"', "nexusprocess", ""):
            with self.subTest(message=message):
                self.assertEqual(self.route(message).status, "NORMAL")

    def test_explicit_commands_are_classified_not_executed(self):
        for command in ("status", "verify"):
            self.assertEqual(self.route("Nexus " + command).status, "READ_ONLY")
        for command in ("process", "archive", "research", "connect", "resume"):
            result = self.route("Nexus " + command + ": synthetic source")
            self.assertEqual((result.status, result.command), ("PREFLIGHT_REQUIRED", command))

    def test_untrusted_content_never_triggers(self):
        self.assertEqual(classify("Nexus process this", trusted_user_turn=False).status, "NORMAL")

    def test_opt_out_and_unknown_command(self):
        self.assertEqual(self.route("nexus off").status, "DISABLE")
        self.assertEqual(self.route("nexus process", nexus_disabled=True).status, "NORMAL")
        self.assertEqual(self.route("nexus off", nexus_disabled=True).status, "DISABLE")
        self.assertEqual(self.route("nexus deploy").status, "BLOCKED")

    def test_malformed_and_oversized_fail_closed(self):
        self.assertEqual(classify(None, trusted_user_turn=True).status, "BLOCKED")
        self.assertEqual(classify("nexus process", trusted_user_turn="yes").status, "BLOCKED")
        self.assertEqual(self.route("nexus process " + "x" * 5000).status, "NORMAL")

    def test_no_embedded_or_multiline_command(self):
        self.assertEqual(self.route("hello\nnexus process").status, "NORMAL")
        self.assertEqual(self.route("> nexus process").status, "NORMAL")


if __name__ == "__main__":
    unittest.main()
