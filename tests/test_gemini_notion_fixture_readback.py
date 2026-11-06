import unittest
from tools.gemini_notion_fixture_readback import observe_fixture, FIXTURE_ID


class ReadbackBoundaryTests(unittest.TestCase):
    def test_refuses_write_transport(self):
        def request(method, path, payload):
            if method != "GET":
                raise AssertionError("Unexpected write")
            if path == "/v1/pages/" + FIXTURE_ID:
                return {"object": "page", "id": FIXTURE_ID,
                        "archived": False, "in_trash": False}
            return {"object": "list", "results": [], "has_more": False,
                    "next_cursor": None}
        result = observe_fixture(request)
        self.assertEqual(result["writes_attempted"], 0)
        self.assertEqual(result["result"], "FIXTURE_READ_ONLY_OBSERVED")

    def test_refuses_wrong_page(self):
        def request(method, path, payload):
            return {"object": "page", "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    "archived": False, "in_trash": False}
        with self.assertRaises(ValueError):
            observe_fixture(request)

    def test_refuses_unavailable_inventory(self):
        def request(method, path, payload):
            if path.startswith("/v1/pages/"):
                return {"object": "page", "id": FIXTURE_ID,
                        "archived": False, "in_trash": False}
            raise ValueError("Notion unavailable")
        with self.assertRaises(ValueError):
            observe_fixture(request)


if __name__ == "__main__":
    unittest.main()
