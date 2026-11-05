"""Pure fail-closed CP05 Notion snapshot checks. No provider calls or writes."""
import hashlib
import json

EXPECTED_PAGE = "40e8c067-daa4-8199-9f12-c9b6486de444"
EXPECTED_PAYLOAD = "The copper lantern stays lit at dawn."

def check_snapshot(before, blocks, after):
    for page in (before, after):
        if not isinstance(page, dict) or page.get("id", "").replace("-", "") != EXPECTED_PAGE.replace("-", ""):
            raise ValueError("page identity mismatch")
        if not isinstance(page.get("last_edited_time"), str) or not page["last_edited_time"]:
            raise ValueError("missing provider revision")
    if before["last_edited_time"] != after["last_edited_time"]:
        raise ValueError("source revision changed during read")
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("empty source inventory")
    normalized = []
    for block in blocks:
        if not isinstance(block, dict) or block.get("has_children"):
            raise ValueError("nested or malformed block")
        kind = block.get("type")
        data = block.get(kind)
        if not isinstance(kind, str) or not isinstance(data, dict) or not isinstance(data.get("rich_text"), list):
            raise ValueError("unsupported block inventory")
        parts = data["rich_text"]
        if not all(isinstance(part, dict) and isinstance(part.get("plain_text"), str) for part in parts):
            raise ValueError("malformed rich text")
        normalized.append({"id": block.get("id"), "type": kind, "plain_text": "".join(part["plain_text"] for part in parts)})
    payload = "\n".join(item["plain_text"] for item in normalized)
    if payload != EXPECTED_PAYLOAD:
        raise ValueError("fixture must match exactly")
    inventory = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return {"source_revision": before["last_edited_time"], "block_count": len(normalized),
            "canonical_inventory_sha256": hashlib.sha256(inventory).hexdigest(),
            "fixture_payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
            "checkpoint": "NOT_ATTESTED", "provider_writes": 0}
