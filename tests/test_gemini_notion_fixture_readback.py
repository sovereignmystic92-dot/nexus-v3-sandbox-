import unittest
from tools.gemini_notion_fixture_readback import observe_fixture, FIXTURE_ID

BLOCK_ID = "11111111111141118111111111111111"


def fixture_request(*, text="The copper lantern stays lit at dawn.", wrong_page=False,
                    unavailable=False, malformed=False):
    def request(method, path, payload):
        if method != "GET" or payload is not None:
            raise AssertionError("Unexpected write")
        if path == "/v1/pages/" + FIXTURE_ID:
            return {"object": "page", "id": BLOCK_ID if wrong_page else FIXTURE_ID,
                    "archived": False, "in_trash": False}
        if unavailable:
            raise ValueError("Notion unavailable")
        block = {"object": "block", "id": BLOCK_ID,
                 "parent": {"type": "page_id", "page_id": FIXTURE_ID},
                 "type": "paragraph", "has_children": False,
                 "archived": False, "in_trash": False,
                 "paragraph": {"rich_text": [{"type": "text", "plain_text": text,
                                             "text": {"content": text}}]}}
        if malformed:
            block["parent"]["page_id"] = BLOCK_ID
        return {"object": "list", "results": [block],
                "has_more": False, "next_cursor": None}
    return request


class ReadbackBoundaryTests(unittest.TestCase):
    def test_verified_fixture_text(self):
        result = observe_fixture(fixture_request())
        self.assertEqual(result["writes_attempted"], 0)
        self.assertEqual(result["result"], "FIXTURE_CONTENT_MATCHED_READ_ONLY")
        self.assertEqual(result["blocks_observed"], 1)
        self.assertEqual(result["read_requests"], 2)

    def test_refuses_wrong_page(self):
        with self.assertRaises(ValueError):
            observe_fixture(fixture_request(wrong_page=True))

    def test_refuses_unavailable_inventory(self):
        with self.assertRaises(ValueError):
            observe_fixture(fixture_request(unavailable=True))

    def test_refuses_missing_fixture_phrase(self):
        with self.assertRaises(ValueError):
            observe_fixture(fixture_request(text="Unrelated synthetic text"))

    def test_refuses_mismatched_block_parent(self):
        with self.assertRaises(ValueError):
            observe_fixture(fixture_request(malformed=True))


if __name__ == "__main__":
    unittest.main()
