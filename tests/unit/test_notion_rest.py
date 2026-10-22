"""Offline REST shapes and pagination; no network requests or credentials."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from nexus_sandbox.notion_adapter import Binding, NotionAdapter
from nexus_sandbox.notion_rest import API_VERSION, IncompleteObservation, MARKER, NotionRESTTransport

ROOT = "00000000-0000-0000-0000-000000000001"
PAGE = "00000000-0000-0000-0000-000000000002"
OTHER = "00000000-0000-0000-0000-000000000003"


def rich(value):
    return [{"type": "text", "text": {"content": value}}]


def block(identifier, kind, value):
    result = {"object": "block", "id": identifier, "type": kind, "has_children": False}
    result[kind] = {"rich_text": rich(value)}
    if kind == "code":
        result[kind]["language"] = "json"
    return result


def listing(blocks, cursor=None):
    return {"object": "list", "results": blocks, "has_more": cursor is not None, "next_cursor": cursor}


class Service:
    def __init__(self):
        self.calls = []
        self.root_blocks = [block(OTHER, "paragraph", MARKER)]
        self.child_blocks = []
        self.parent = ROOT
        self.title = "Synthetic REST fixture"
        self.lose_post = False
        self.page_exists = False
        self.override = None

    def __call__(self, method, path, *, query, body, headers):
        self.calls.append((method, path, deepcopy(query), deepcopy(body), headers))
        if self.override:
            value = self.override(method, path, query)
            if value is not None:
                return value
        if path.startswith("/blocks/"):
            return listing(deepcopy(self.root_blocks if ROOT in path else self.child_blocks))
        if method == "GET":
            return {"object": "page", "id": ROOT if path.endswith(ROOT) else PAGE,
                    "parent": {"type": "page_id", "page_id": self.parent},
                    "properties": {"title": {"type": "title", "title": rich(self.title)}},
                    "in_trash": False, "archived": False}
        self.page_exists = True
        self.title = body["properties"]["title"]["title"][0]["text"]["content"]
        self.child_blocks = [dict(deepcopy(body["children"][0]), id=OTHER, has_children=False)]
        self.root_blocks.append({"object": "block", "id": PAGE, "type": "child_page", "has_children": False, "child_page": {"title": self.title}})
        if self.lose_post:
            raise TimeoutError("synthetic lost acknowledgment")
        return {"object": "page", "id": PAGE}


class RESTTransportTests(unittest.TestCase):
    def setUp(self):
        self.service = Service()
        self.transport = NotionRESTTransport(ROOT, self.service)
        self.binding = Binding("synthetic:request:rest", ROOT, self.service.title, "Fictional API payload")
        temporary = tempfile.TemporaryDirectory(prefix="notion-rest-offline-")
        self.addCleanup(temporary.cleanup)
        self.journal = Path(temporary.name) / "rest.sqlite"

    def engine(self):
        return NotionAdapter(self.journal, ROOT, self.transport)

    def post_count(self):
        return sum(c[0] == "POST" for c in self.service.calls)

    def test_full_engine_create_readback_repeat_uses_one_post(self):
        self.assertEqual(self.engine().ensure(self.binding).status, "VERIFIED")
        self.assertEqual(self.engine().ensure(self.binding).status, "VERIFIED")
        self.assertEqual(self.post_count(), 1)
        self.assertTrue(all(c[4] == {"Notion-Version": API_VERSION} for c in self.service.calls))
        self.assertTrue(all(c[0] in ("GET", "POST") for c in self.service.calls))

    def test_lost_post_response_reconciles_without_second_post(self):
        self.service.lose_post = True
        self.assertEqual(self.engine().ensure(self.binding).status, "UNKNOWN")
        self.assertEqual(self.engine().ensure(self.binding).status, "VERIFIED")
        self.assertEqual(self.post_count(), 1)

    def test_multiple_root_pages_are_fully_requested(self):
        first = self.service.root_blocks[0]
        second = block(PAGE, "paragraph", "Second page")
        def response(method, path, query):
            if path == "/blocks/" + ROOT + "/children":
                return listing([second]) if query.get("start_cursor") else listing([first], "cursor-2")
        self.service.override = response
        result = self.transport.find_direct_children(ROOT, self.binding.key)
        self.assertTrue(result.complete)
        self.assertEqual([c[2].get("start_cursor") for c in self.service.calls], [None, "cursor-2"])

    def test_looping_cursor_and_pagination_exhaustion_fail_closed(self):
        for cursor_mode in ("same", "changing"):
            self.transport = NotionRESTTransport(ROOT, self.service, max_pages=2)
            count = [0]
            def response(method, path, query):
                count[0] += 1
                return listing([], "repeat" if cursor_mode == "same" else str(count[0]))
            self.service.override = response
            with self.subTest(mode=cursor_mode), self.assertRaises(IncompleteObservation):
                self.transport.find_direct_children(ROOT, self.binding.key)
        self.assertEqual(self.post_count(), 0)

    def test_missing_has_more_and_duplicate_block_ids_are_rejected(self):
        for response in ({"object": "list", "results": []}, listing([self.service.root_blocks[0]] * 2)):
            self.service.override = lambda *args: response
            with self.subTest(response=response), self.assertRaises(IncompleteObservation):
                self.transport.find_direct_children(ROOT, self.binding.key)

    def test_rate_limit_error_holds_without_post_or_retry(self):
        self.service.override = lambda *args: {"object": "error", "code": "rate_limited", "status": 429}
        self.assertEqual(self.engine().ensure(self.binding).status, "BLOCKED")
        self.assertEqual(len(self.service.calls), 1)
        self.assertEqual(self.post_count(), 0)

    def test_wrong_parent_rejected_before_reading_page_body(self):
        self.service.parent = OTHER
        with self.assertRaises(IncompleteObservation):
            self.transport.fetch_page(PAGE)
        self.assertEqual([c[1] for c in self.service.calls], ["/pages/" + PAGE])

    def test_outside_create_target_rejected_before_any_request(self):
        with self.assertRaises(ValueError):
            self.transport.create_child(replace(self.binding, parent_id=OTHER))
        self.assertEqual(self.service.calls, [])

    def test_nested_or_unsupported_content_never_counts_as_complete(self):
        for change in ({"has_children": True}, {"type": "unsupported"}):
            self.service.root_blocks = [dict(block(OTHER, "paragraph", MARKER), **change)]
            with self.subTest(change=change), self.assertRaises(IncompleteObservation):
                self.transport.find_direct_children(ROOT, self.binding.key)

    def test_multiple_records_or_nonboolean_synthetic_are_rejected(self):
        self.transport.create_child(self.binding)
        original = deepcopy(self.service.child_blocks)
        self.service.child_blocks.append(dict(deepcopy(original[0]), id=ROOT))
        with self.assertRaises(IncompleteObservation):
            self.transport.fetch_page(PAGE)
        self.service.child_blocks = original
        record = json.loads(original[0]["code"]["rich_text"][0]["text"]["content"])
        record["synthetic"] = 1
        self.service.child_blocks[0]["code"]["rich_text"] = rich(json.dumps(record))
        with self.assertRaises(IncompleteObservation):
            self.transport.fetch_page(PAGE)

    def test_payload_is_split_and_reassembled_without_loss(self):
        binding = replace(self.binding, payload="Synthetic emoji 🌱 " * 2500)
        self.assertEqual(self.engine().ensure(binding).status, "VERIFIED")
        parts = self.service.child_blocks[0]["code"]["rich_text"]
        self.assertTrue(all(len(p["text"]["content"]) <= 1500 for p in parts))
        self.assertGreater(len(parts), 1)

    def test_json_escape_expansion_is_bounded_before_post(self):
        binding = replace(self.binding, payload="\x00" * 65536)
        with self.assertRaises(ValueError):
            self.transport.create_child(binding)
        self.assertEqual(self.post_count(), 0)

    def test_request_budget_stops_unbounded_transport_use(self):
        self.transport.calls = 200
        with self.assertRaises(IncompleteObservation):
            self.transport.sandbox_marker(ROOT)
        self.assertEqual(self.service.calls, [])

    def test_literal_page_mentions_in_prose_do_not_hide_records(self):
        self.transport.create_child(self.binding)
        prose = block(ROOT, "paragraph", "")
        prose["paragraph"]["rich_text"] = [{"type": "mention", "plain_text": "Synthetic source"}]
        self.service.child_blocks.insert(0, prose)
        self.assertEqual(self.transport.fetch_page(PAGE).payload, self.binding.payload)
