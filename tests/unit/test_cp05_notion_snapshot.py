"""Adversarial unit tests for CP05 source snapshot integrity."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import unittest
from cp05_notion_snapshot import check_snapshot, EXPECTED_PAGE, EXPECTED_PAYLOAD

def page(revision="2026-11-04T21:14:09.277Z"):
    return {"id": EXPECTED_PAGE, "last_edited_time": revision}

def blocks(text=None):
    if text is None:
        text = "Expected payload: " + EXPECTED_PAYLOAD
    return [{"id": "fixture-block", "type": "paragraph", "has_children": False,
             "paragraph": {"rich_text": [{"plain_text": text}]}}]

class SnapshotTests(unittest.TestCase):
    def test_valid_fixture_and_inventory_digest(self):
        receipt = check_snapshot(page(), blocks(), page())
        self.assertEqual(receipt["block_count"], 1)
        self.assertEqual(len(receipt["canonical_inventory_sha256"]), 64)
        self.assertEqual(receipt["provider_writes"], 0)
    def test_changed_revision_fails(self):
        with self.assertRaises(ValueError):
            check_snapshot(page(), blocks(), page("2026-11-05T00:00:00Z"))
    def test_wrong_page_fails(self):
        with self.assertRaises(ValueError):
            check_snapshot({"id": "wrong", "last_edited_time": "a"}, blocks(), page())
    def test_substring_not_accepted(self):
        with self.assertRaises(ValueError):
            check_snapshot(page(), blocks("prefix Expected payload: " + EXPECTED_PAYLOAD), page())
    def test_duplicate_fixture_line_fails(self):
        line = "Expected payload: " + EXPECTED_PAYLOAD
        with self.assertRaises(ValueError):
            check_snapshot(page(), blocks(line + "\n" + line), page())
    def test_nested_and_malformed_blocks_fail(self):
        for bad in ([], [{"id": "a", "type": "paragraph", "has_children": True, "paragraph": {"rich_text": []}}],
                    [{"id": "a", "type": "paragraph", "paragraph": {"rich_text": [{"plain_text": 4}]}}]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                check_snapshot(page(), bad, page())

if __name__ == "__main__":
    unittest.main()
