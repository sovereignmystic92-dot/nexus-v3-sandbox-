"""Offline tests for bounded source envelope CLI."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from nexus_sandbox.csf_v02 import CSFValidationError


class TestNotionIntakeCLI(unittest.TestCase):
    def test_cli_source_integrity(self):
        import importlib.util
        script = Path(__file__).resolve().parents[2] / "tools" / "prepare_csf_notion_intake.py"
        if not script.is_file():
            self.skipTest("CLI excluded from isolated runtime")
        spec = importlib.util.spec_from_file_location("csf_notion_intake_cli", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        raw = "Paragraph one.\n\nParagraph two."
        source = {
            "source_url": "https://app.notion.com/p/4088c067daa4813bb1f0e1f1993120fb",
            "source_revision": "2026-10-29T23:44:29.194Z",
            "document_id": "notion:4088c067-daa4-813b-b1f0-e1f1993120fb",
            "transcript": raw,
            "expected_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        }
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "source.json"
            p.write_text(json.dumps(source), encoding="utf-8")
            self.assertEqual(module.prepare(p)["segment_count"], 2)
            source["transcript"] = raw + " changed"
            p.write_text(json.dumps(source), encoding="utf-8")
            with self.assertRaises(CSFValidationError):
                module.prepare(p)


if __name__ == "__main__":
    unittest.main()
