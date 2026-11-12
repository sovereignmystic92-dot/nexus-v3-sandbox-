import unittest
from nexus_sandbox.chat_cortex_notion_fetch import fetch_canonical, SOURCE_ID

class NotionFetchTests(unittest.TestCase):
    def test_no_credential_fails_closed(self):
        with self.assertRaises(ValueError):
            fetch_canonical("")
    def test_pagination_and_revision(self):
        calls = []
        def api(path, token):
            calls.append(path)
            if path.startswith("pages/"):
                return {"id": SOURCE_ID, "last_edited_time": "2026-11-12T20:00:00Z"}
            if "start_cursor" not in path:
                return {"results": [{"type": "heading_2", "has_children": False,
                    "heading_2": {"rich_text": [{"plain_text": "Raw chunk 0"}]}}],
                    "has_more": True, "next_cursor": "next"}
            return {"results": [{"type": "code", "has_children": False,
                "code": {"language": "plain text", "rich_text": [{"plain_text": "abc"}]}}],
                "has_more": False}
        markdown, metadata = fetch_canonical("test", api=api)
        self.assertIn("## Raw chunk 0", markdown)
        self.assertIn("```txt\nabc\n```", markdown)
        self.assertEqual(metadata["source_revision"], "2026-11-12T20:00:00Z")
        self.assertEqual(len(calls), 4)
    def test_unknown_blocks_fail_closed(self):
        def api(path, token):
            if path.startswith("pages/"):
                return {"id": SOURCE_ID, "last_edited_time": "revision"}
            return {"results": [{"type": "image", "has_children": False}],
                    "has_more": False}
        with self.assertRaises(ValueError):
            fetch_canonical("test", api=api)

if __name__ == "__main__":
    unittest.main()
