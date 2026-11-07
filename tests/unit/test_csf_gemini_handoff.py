"""Offline synthetic tests for pinned Gemini CSF handoff preparation."""
import json
from pathlib import Path
import tempfile
import unittest

from nexus_sandbox.csf_gemini_handoff import (
    ALLOWED_PATHS, HandoffError, build_handoff,
)

SHA = "a" * 40


class GeminiHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for relative in ALLOWED_PATHS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"synthetic":true}' if relative.endswith(".json") else "# synthetic\n", encoding="utf-8")

    def test_manifest_is_stable_and_not_execution(self):
        first = build_handoff(self.root, SHA)
        self.assertEqual(first, build_handoff(self.root, SHA))
        self.assertEqual(first["status"], "PREPARED_NOT_EXECUTED")
        self.assertEqual(len(first["sources"]), len(ALLOWED_PATHS))

    def test_missing_source_rejected(self):
        (self.root / ALLOWED_PATHS[0]).unlink()
        with self.assertRaises(HandoffError):
            build_handoff(self.root, SHA)

    def test_invalid_json_rejected(self):
        (self.root / ALLOWED_PATHS[0]).write_text("{", encoding="utf-8")
        with self.assertRaises(HandoffError):
            build_handoff(self.root, SHA)

    def test_moving_ref_rejected(self):
        with self.assertRaises(HandoffError):
            build_handoff(self.root, "main")

    def test_oversized_source_rejected(self):
        (self.root / ALLOWED_PATHS[2]).write_text("x" * 128001, encoding="utf-8")
        with self.assertRaises(HandoffError):
            build_handoff(self.root, SHA)

    def test_source_change_changes_digest(self):
        first = build_handoff(self.root, SHA)
        (self.root / ALLOWED_PATHS[2]).write_text("# modified synthetic\n", encoding="utf-8")
        second = build_handoff(self.root, SHA)
        self.assertNotEqual(first["sources"][2]["sha256"], second["sources"][2]["sha256"])


if __name__ == "__main__":
    unittest.main()
