"""Authenticated read-only Notion source probe for the first real CSF transcript.

Prints metadata only. Does not export transcript, create candidates or write data.
"""
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

PAGE_ID = "4088c067-daa4-813b-b1f0-e1f1993120fb"
API = "https://api.notion.com/v1/"
MAX_BLOCKS = 500
MAX_DEPTH = 4


def read_json(path, token):
    request = urllib.request.Request(
        API + path,
        headers={"Authorization": "Bearer " + token, "Notion-Version": "2022-06-28",
                 "Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.status != 200:
            raise ValueError("non-200 Notion response")
        return json.load(response)


def children(block_id, token, depth=0, budget=None):
    if budget is None:
        budget = [MAX_BLOCKS]
    if depth > MAX_DEPTH:
        raise ValueError("nested block depth exceeded")
    result = []
    cursor = None
    while True:
        path = "blocks/" + block_id + "/children?page_size=100"
        if cursor:
            path += "&start_cursor=" + urllib.parse.quote(cursor, safe="")
        page = read_json(path, token)
        entries = page.get("results")
        if not isinstance(entries, list):
            raise ValueError("missing block inventory")
        budget[0] -= len(entries)
        if budget[0] < 0:
            raise ValueError("block inventory limit exceeded")
        for entry in entries:
            result.append(entry)
            if entry.get("has_children"):
                result.extend(children(entry["id"], token, depth + 1, budget))
        if not page.get("has_more"):
            return result
        cursor = page.get("next_cursor")
        if not cursor:
            raise ValueError("pagination cursor missing")


def extract_raw(blocks):
    # Require an explicitly labeled RAW-001 section, not a guessed article body.
    seen_heading = False
    chunks = []
    for block in blocks:
        kind = block.get("type")
        data = block.get(kind, {})
        rich = data.get("rich_text", []) if isinstance(data, dict) else []
        if not isinstance(rich, list):
            raise ValueError("unsupported rich text")
        text = "".join(item.get("plain_text", "") for item in rich)
        if kind in ("heading_1", "heading_2", "heading_3") and "RAW-001" in text:
            if seen_heading:
                raise ValueError("duplicate RAW-001 heading")
            seen_heading = True
            continue
        if seen_heading and kind in ("heading_1", "heading_2", "heading_3"):
            break
        if seen_heading and kind == "code":
            chunks.append(text)
    if not seen_heading or len(chunks) != 1 or not chunks[0].strip():
        raise ValueError("exactly one RAW-001 code block required")
    return chunks[0]


def probe(token):
    page = read_json("pages/" + PAGE_ID, token)
    if page.get("id", "").replace("-", "") != PAGE_ID.replace("-", ""):
        raise ValueError("page identity mismatch")
    if page.get("archived") or page.get("in_trash"):
        raise ValueError("archived source")
    revision = page.get("last_edited_time")
    if not isinstance(revision, str) or not revision:
        raise ValueError("missing revision")
    blocks = children(PAGE_ID, token)
    raw = extract_raw(blocks)
    # Re-read page metadata to reject a changed source during inventory.
    again = read_json("pages/" + PAGE_ID, token)
    if again.get("last_edited_time") != revision:
        raise ValueError("source changed during read")
    return {"status": "NOTION_SOURCE_READ_ONLY", "page_id": PAGE_ID,
            "source_revision": revision, "utf8_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "utf16_code_units": len(raw.encode("utf-16-le")) // 2,
            "block_count": len(blocks), "external_writes": 0,
            "csf_processed": False, "audit_gate_promoted": False}



def prepare_live_segments(token):
    """Read canonical source twice, then segment in memory without emitting raw text."""
    page = read_json("pages/" + PAGE_ID, token)
    if page.get("id", "").replace("-", "") != PAGE_ID.replace("-", ""):
        raise ValueError("page identity mismatch")
    if page.get("archived") or page.get("in_trash"):
        raise ValueError("archived source")
    revision = page.get("last_edited_time")
    if not isinstance(revision, str) or not revision:
        raise ValueError("missing revision")
    blocks = children(PAGE_ID, token)
    raw = extract_raw(blocks)
    again = read_json("pages/" + PAGE_ID, token)
    if again.get("id", "").replace("-", "") != PAGE_ID.replace("-", "") or again.get("last_edited_time") != revision:
        raise ValueError("source changed during read")
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from nexus_sandbox.csf_notional_intake import prepare_source_receipt
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    receipt = prepare_source_receipt({
        "source_url": "https://app.notion.com/p/" + PAGE_ID.replace("-", ""),
        "source_revision": revision,
        "document_id": PAGE_ID,
        "transcript": raw,
        "expected_sha256": digest,
    })
    if os.environ.get("NOTION_CSF_BOUNDED") == "true":
        from nexus_sandbox.csf_transcript_ingest import segment_transcript_bounded
        bounded = segment_transcript_bounded(PAGE_ID, raw)
        if bounded["content_digest"] != digest:
            raise ValueError("bounded digest mismatch")
        return {"status": "NOTION_CSF_BOUNDED_READ_ONLY",
                "page_id": PAGE_ID, "source_revision": revision,
                "content_digest": digest, "segment_count": bounded["segment_count"],
                "offsets_verified": all(raw[v["start"]:v["end"]] and
                  hashlib.sha256(raw[v["start"]:v["end"]].encode("utf-8")).hexdigest() == v["sha256"]
                  for v in bounded["spans"].values()),
                "candidates": 0, "provider_called": False, "external_writes": 0,
                "audit_gate_promoted": False}
    return {"status": "NOTION_CSF_SEGMENTS_READ_ONLY",
            "page_id": PAGE_ID, "source_revision": revision,
            "content_digest": receipt["content_digest"],
            "segment_count": receipt["segment_count"],
            "candidates": 0, "provider_called": False,
            "external_writes": 0, "audit_gate_promoted": False}


def identity_probe(token):
    """Read token principal only; never emit bearer token or provider response body."""
    try:
        me = read_json("users/me", token)
    except urllib.error.HTTPError as exc:
        return {"status": "IDENTITY_BLOCKED_HTTP", "http_status": int(exc.code),
                "external_writes": 0}
    bot = me.get("bot", {}) if isinstance(me, dict) else {}
    owner = bot.get("owner", {}) if isinstance(bot, dict) else {}
    return {"status": "IDENTITY_READ_ONLY", "principal_type": me.get("type"),
            "principal_id": me.get("id"), "principal_name": me.get("name"),
            "workspace_name": bot.get("workspace_name"),
            "owner_type": owner.get("type") if isinstance(owner, dict) else None,
            "external_writes": 0}


def main():
    token = os.environ.get("NOTION_SANDBOX_TOKEN", "")
    if not token:
        print('{"status":"BLOCKED","reason":"credential_unavailable"}')
        return 2
    try:
        if os.environ.get("NOTION_IDENTITY_ONLY") == "true":
            result = identity_probe(token)
            print(json.dumps(result, sort_keys=True))
            return 0 if result["status"] == "IDENTITY_READ_ONLY" else 2
        if os.environ.get("NOTION_CSF_SEGMENTS_ONLY") == "true":
            print(json.dumps(prepare_live_segments(token), sort_keys=True))
            return 0
        print(json.dumps(probe(token), sort_keys=True))
        return 0
    except urllib.error.HTTPError as exc:
        print(json.dumps({"status": "BLOCKED_HTTP", "http_status": int(exc.code),
                          "external_writes": 0}))
        return 2
    except (ValueError, KeyError, TypeError, urllib.error.URLError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": type(exc).__name__,
                          "external_writes": 0}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
