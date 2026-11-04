"""Offline contract tests for Notion REST fixture reader."""
import io
import json
from nexus_sandbox.cp05_notion_rest_reader import read_notion_fixture


class Response:
    status = 200
    def __init__(self, payload):
        self.body = io.BytesIO(json.dumps(payload).encode())
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, limit):
        return self.body.read(limit)


def test_authenticated_pagination_reads_every_page():
    urls = []
    def opener(req, timeout):
        urls.append(req.full_url)
        if "/pages/" in req.full_url:
            return Response({"id": "page-1", "last_edited_time": "2026-11-04T15:38:03.604Z"})
        if "start_cursor=" in req.full_url:
            return Response({"results": [{"type": "paragraph",
                "paragraph": {"rich_text": [{"plain_text": "dawn."}]}}],
                "has_more": False})
        return Response({"results": [{"type": "paragraph",
            "paragraph": {"rich_text": [{"plain_text": "The copper lantern stays lit at"}]}}],
            "has_more": True, "next_cursor": "next"})
    result, meta = read_notion_fixture("page-1", token="placeholder", opener=opener)
    assert result["blocks_count"] == 2
    assert result["text"] == "The copper lantern stays lit at\ndawn."
    assert meta["complete_inventory"] is True
    assert len(urls) == 3


def test_nested_blocks_fail_closed():
    def opener(req, timeout):
        if "/pages/" in req.full_url:
            return Response({"id": "page-1"})
        return Response({"results": [{"has_children": True}], "has_more": False})
    try:
        read_notion_fixture("page-1", token="placeholder", opener=opener)
    except ValueError as exc:
        assert "Nested" in str(exc)
    else:
        raise AssertionError("Expected fail closed")
