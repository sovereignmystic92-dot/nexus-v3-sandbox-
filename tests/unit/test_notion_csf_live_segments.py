"""Offline checks for live Notion-to-CSF metadata-only bridge."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "notion_csf_authenticated_source_probe.py"
spec = importlib.util.spec_from_file_location("notion_probe_live_segments", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class LiveSegmentTests(unittest.TestCase):
    def test_live_segments_metadata_only(self):
        raw = "One sentence. Another sentence."
        page = {"id": mod.PAGE_ID, "last_edited_time": "2026-11-07T00:00:00Z"}
        blocks = [
            {"type": "heading_2", "heading_2": {"rich_text": [{"plain_text": "RAW-001"}]}},
            {"type": "code", "code": {"rich_text": [{"plain_text": raw}]}},
        ]
        with patch.object(mod, "read_json", return_value=page) as read, patch.object(mod, "children", return_value=blocks):
            result = mod.prepare_live_segments("fake-token")
        self.assertEqual(result["status"], "NOTION_CSF_SEGMENTS_READ_ONLY")
        self.assertGreater(result["segment_count"], 0)
        self.assertEqual(result["external_writes"], 0)
        self.assertEqual(result["candidates"], 0)
        self.assertNotIn("segments", result)
        self.assertNotIn("transcript", result)
        self.assertEqual(read.call_count, 2)

    def test_changed_revision_fails_closed(self):
        pages = [
            {"id": mod.PAGE_ID, "last_edited_time": "old"},
            {"id": mod.PAGE_ID, "last_edited_time": "new"},
        ]
        with patch.object(mod, "read_json", side_effect=pages), patch.object(mod, "children", return_value=[{"type": "heading_2", "heading_2": {"rich_text": [{"plain_text": "RAW-001"}]}}, {"type": "code", "code": {"rich_text": [{"plain_text": "A valid transcript."}]}}]):
            with self.assertRaisesRegex(ValueError, "source changed"):
                mod.prepare_live_segments("fake-token")


if __name__ == "__main__":
    unittest.main()
