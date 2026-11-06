"""Synthetic tests for Git checkout identity preflight of CSF handoff."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from nexus_sandbox.csf_gemini_handoff import ALLOWED_PATHS, HandoffError
from tools.prepare_csf_gemini_handoff import prepare


class GeminiCheckoutPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Synthetic",
                        "-c", "user.email=synthetic@example.invalid",
                        "commit", "--allow-empty", "-qm", "synthetic"], check=True, capture_output=True)
        self.sha = subprocess.run(["git", "-C", str(self.root), "rev-parse", "HEAD"],
                                  check=True, capture_output=True, text=True).stdout.strip()
        for relative in ALLOWED_PATHS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"synthetic":true}' if relative.endswith(".json") else "# synthetic\n")

    def test_matching_checkout_produces_prepared_not_executed(self):
        result = prepare(self.root, self.sha)
        self.assertEqual(result["source_commit"], self.sha)
        self.assertEqual(result["status"], "PREPARED_NOT_EXECUTED")

    def test_wrong_checkout_sha_blocks(self):
        with self.assertRaisesRegex(HandoffError, "checkout HEAD differs"):
            prepare(self.root, "0" * 40)

    def test_moving_ref_blocks(self):
        with self.assertRaises(HandoffError):
            prepare(self.root, "main")


if __name__ == "__main__":
    unittest.main()
