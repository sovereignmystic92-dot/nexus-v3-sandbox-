"""Notion REST request mapping using an injected authenticated request gateway.

No HTTP client, token lookup or automatic network execution is included. The
gateway must restrict the origin to https://api.notion.com/v1, set a timeout,
bound response sizes, protect credentials and never retry POST automatically.
"""

import json
import re
from uuid import UUID

from .notion_adapter import Binding, Listing, Page

API_VERSION = "2026-03-11"
MARKER = "Sandbox marker: synthetic:notion:sandbox:v1"


def create_body(binding):
    if (not re.fullmatch(r"synthetic:request:[A-Za-z0-9_-]+", binding.key)
            or not isinstance(binding.title, str) or not 1 <= len(binding.title) <= 200
            or not isinstance(binding.payload, str) or len(binding.payload.encode()) > 65536):
        raise ValueError("Create outside bounded synthetic contract")
    record = {"adapter_schema": 1, "key": binding.key, "title": binding.title,
              "payload": binding.payload, "payload_sha256": binding.payload_sha256, "synthetic": True}
    encoded = json.dumps(record, ensure_ascii=False, sort_keys=True)
    rich = [{"type": "text", "text": {"content": encoded[i:i + 1500]}}
            for i in range(0, len(encoded), 1500)]
    if len(rich) > 100:
        raise ValueError("Escaped JSON exceeds bounded rich-text array size")
    return {"parent": {"page_id": binding.parent_id},
            "properties": {"title": {"title": [{"type": "text", "text": {"content": binding.title}}]}},
            "children": [{"object": "block", "type": "code", "code": {"language": "json", "rich_text": rich}}]}


class IncompleteObservation(ValueError):
    pass


def uuid_key(value):
    return UUID(value).hex


def text(items):
    if not isinstance(items, list) or len(items) > 100:
        raise IncompleteObservation("Rich text missing or exceeds bound")
    parts = []
    for item in items:
        # Adapter records and titles use literal text, not linked mentions.
        if item.get("type") != "text" or not isinstance(item.get("text", {}).get("content"), str):
            raise IncompleteObservation("Unsupported rich text")
        parts.append(item["text"]["content"])
    result = "".join(parts)
    if len(result.encode()) > 100000:
        raise IncompleteObservation("Rich text exceeds byte bound")
    return result


def paragraph_text(items):
    # Ordinary prose may contain Notion page mentions; adapter JSON and titles
    # still require literal text. Read-only plain_text is never executed.
    parts = []
    if not isinstance(items, list) or len(items) > 100:
        raise IncompleteObservation("Incomplete paragraph")
    for item in items:
        if item.get("type") == "mention" and isinstance(item.get("plain_text"), str):
            parts.append(item["plain_text"])
        else:
            parts.append(text([item]))
    value = "".join(parts)
    if len(value.encode()) > 100000:
        raise IncompleteObservation("Paragraph exceeds byte bound")
    return value


class NotionRESTTransport:
    def __init__(self, sandbox_parent, request, *, max_pages=10):
        uuid_key(sandbox_parent)
        if type(max_pages) is not int or not 1 <= max_pages <= 10:
            raise ValueError("Pagination bound must be 1 through 10")
        self.parent = sandbox_parent
        self.request = request
        self.max_pages = max_pages
        self.calls = 0

    def _call(self, method, path, *, query=None, body=None):
        self.calls += 1
        if self.calls > 200:
            raise IncompleteObservation("Transport lifetime request budget exceeded")
        response = self.request(method, path, query=query, body=body,
                                headers={"Notion-Version": API_VERSION})
        if not isinstance(response, dict) or response.get("object") == "error":
            raise IncompleteObservation("Notion request did not return a successful object")
        return response

    def _blocks(self, page_id):
        uuid_key(page_id)
        blocks, seen, cursors = [], set(), set()
        cursor = None
        for _ in range(self.max_pages):
            query = {"page_size": 100}
            if cursor is not None:
                query["start_cursor"] = cursor
            response = self._call("GET", "/blocks/" + page_id + "/children", query=query)
            batch = response.get("results")
            if (response.get("object") != "list" or not isinstance(batch, list)
                    or len(batch) > 100 or type(response.get("has_more")) is not bool):
                raise IncompleteObservation("Malformed block pagination")
            for block in batch:
                if block.get("object") != "block" or type(block.get("has_children")) is not bool:
                    raise IncompleteObservation("Incomplete block")
                identifier = uuid_key(block["id"])
                if identifier in seen or block.get("in_trash") or block.get("archived"):
                    raise IncompleteObservation("Duplicate or trashed block")
                seen.add(identifier)
                blocks.append(block)
            if response["has_more"] is False:
                if response.get("next_cursor") is not None:
                    raise IncompleteObservation("Inconsistent terminal cursor")
                return blocks
            cursor = response.get("next_cursor")
            if not isinstance(cursor, str) or not cursor or len(cursor) > 1024 or cursor in cursors:
                raise IncompleteObservation("Missing or repeated cursor")
            cursors.add(cursor)
        raise IncompleteObservation("Pagination bound exceeded; no complete lookup")

    def _metadata(self, page_id, *, child=True):
        metadata = self._call("GET", "/pages/" + page_id)
        if (metadata.get("object") != "page" or uuid_key(metadata["id"]) != uuid_key(page_id)
                or metadata.get("in_trash") or metadata.get("archived")):
            raise IncompleteObservation("Page identity or live state mismatch")
        if child:
            parent = metadata.get("parent", {})
            if parent.get("type") != "page_id" or uuid_key(parent.get("page_id")) != uuid_key(self.parent):
                raise IncompleteObservation("Page outside bound root; body not read")
        return metadata

    def sandbox_marker(self, parent_id):
        if uuid_key(parent_id) != uuid_key(self.parent):
            raise ValueError("Root outside allowlist")
        self._metadata(parent_id, child=False)
        for block in self._blocks(parent_id):
            if block["type"] == "paragraph" and not block["has_children"]:
                if text(block["paragraph"]["rich_text"]) == MARKER:
                    return "synthetic:notion:sandbox:v1"
        return "unconfirmed"

    def _record(self, page_id):
        metadata = self._metadata(page_id)
        titles = [p for p in metadata.get("properties", {}).values() if p.get("type") == "title"]
        if len(titles) != 1:
            raise IncompleteObservation("Missing or ambiguous title property")
        title = text(titles[0]["title"])
        records, all_text = [], []
        for block in self._blocks(page_id):
            kind = block["type"]
            if block["has_children"] or kind not in ("paragraph", "code"):
                raise IncompleteObservation("Unsupported or nested artifact content")
            value = (paragraph_text if kind == "paragraph" else text)(block[kind]["rich_text"])
            all_text.append(value)
            if kind == "code":
                if block["code"].get("language") != "json":
                    raise IncompleteObservation("Non-JSON artifact code")
                record = json.loads(value)
                if isinstance(record, dict) and type(record.get("adapter_schema")) is int and record["adapter_schema"] == 1:
                    records.append(record)
        if len(records) > 1:
            raise IncompleteObservation("Multiple adapter records in page")
        if not records:
            return None, "\n".join(all_text)
        record = records[0]
        if (type(record.get("synthetic")) is not bool or record.get("title") != title
                or any(not isinstance(record.get(k), str) for k in ("key", "payload", "payload_sha256"))):
            raise IncompleteObservation("Malformed adapter record")
        return Page(page_id, self.parent, record["key"], title, record["payload"],
                    record["payload_sha256"], record["synthetic"]), "\n".join(all_text)

    def find_direct_children(self, parent_id, key):
        if uuid_key(parent_id) != uuid_key(self.parent):
            raise ValueError("Root outside allowlist")
        matches = []
        for block in self._blocks(parent_id):
            if block["type"] == "child_page":
                page, body = self._record(block["id"])
                if page and page.key == key:
                    matches.append(page)
                elif key in body:
                    raise IncompleteObservation("Requested key appears outside a matching adapter record")
            elif block["has_children"]:
                raise IncompleteObservation("Nested root content requires separate inspection")
            elif block["type"] not in ("paragraph", "heading_1", "heading_2", "heading_3", "heading_4",
                                        "code", "divider", "bulleted_list_item", "numbered_list_item"):
                raise IncompleteObservation("Unsupported root block; no complete lookup")
        return Listing(tuple(matches), True)

    def fetch_page(self, page_id):
        page, _ = self._record(page_id)
        if page is None:
            raise IncompleteObservation("Known page has no adapter record")
        return page

    def create_child(self, binding: Binding):
        if binding.parent_id != self.parent:
            raise ValueError("Create outside bounded synthetic contract")
        body = create_body(binding)
        if self.sandbox_marker(self.parent) != "synthetic:notion:sandbox:v1":
            raise ValueError("Sandbox marker not confirmed immediately before create")
        result = self._call("POST", "/pages", body=body)
        # No automatic retry, even for 429/5xx/timeout. The engine reconciles.
        if result.get("object") != "page":
            raise IncompleteObservation("Create acknowledgment lacks page object")
        uuid_key(result["id"])
        return result["id"]
