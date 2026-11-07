"""Offline tests for authenticated Notion RAW-001 source extraction."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "notion_csf_authenticated_source_probe.py"


class TestNotionSourceProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("notion_source_probe", SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_one_raw_code_block(self):
        blocks = [
            {"type": "heading_2", "heading_2": {"rich_text": [{"plain_text": "RAW-001 — supplied transcript"}]}},
            {"type": "code", "code": {"rich_text": [{"plain_text": "The first "}, {"plain_text": "paragraph."}]}},
        ]
        self.assertEqual(self.module.extract_raw(blocks), "The first paragraph.")

    def test_missing_raw_rejected(self):
        with self.assertRaises(ValueError):
            self.module.extract_raw([{"type": "code", "code": {"rich_text": [{"plain_text": "unbound"}]}}])

    def test_multiple_raw_blocks_rejected(self):
        blocks = [
            {"type": "heading_2", "heading_2": {"rich_text": [{"plain_text": "RAW-001"}]}},
            {"type": "code", "code": {"rich_text": [{"plain_text": "one"}]}},
            {"type": "code", "code": {"rich_text": [{"plain_text": "two"}]}},
        ]
        with self.assertRaises(ValueError):
            self.module.extract_raw(blocks)


if __name__ == "__main__":
    unittest.main()
