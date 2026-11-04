"""Least-privilege Notion REST reader for CP05 test fixture.

No writes, retries, logging of tokens, or implied Nexus host attestation.
Reads all block pages and checks exact fixture text. Nested child blocks are
rejected rather than silently treating a partial inventory as complete.
"""
import json
import urllib.request


def read_notion_fixture(page_id, *, token, opener=None):
    if not isinstance(token, str) or not token.strip():
        raise ValueError("Notion credential missing")
    if not isinstance(page_id, str) or not page_id:
        raise ValueError("Page ID missing")
    open_url = opener or urllib.request.urlopen
    headers = {"Authorization": "Bearer " + token,
               "Notion-Version": "2022-06-28",
               "Accept": "application/json"}

    def get(path):
        req = urllib.request.Request("https://api.notion.com/v1/" + path,
                                     headers=headers, method="GET")
        with open_url(req, timeout=15) as response:
            if response.status != 200:
                raise ValueError("Provider read failed")
            return json.loads(response.read(1048577))

    page = get("pages/" + page_id)
    if page.get("id", "").replace("-", "") != page_id.replace("-", ""):
        raise ValueError("Page identity mismatch")
    blocks, cursor = [], None
    for _ in range(100):
        path = "blocks/" + page_id + "/children?page_size=100"
        if cursor:
            from urllib.parse import quote
            path += "&start_cursor=" + quote(cursor, safe="")
        batch = get(path)
        if not isinstance(batch.get("results"), list):
            raise ValueError("Incomplete Notion response")
        blocks.extend(batch["results"])
        if any(block.get("has_children") for block in batch["results"]):
            raise ValueError("Nested block inventory not supported")
        if not batch.get("has_more"):
            break
        cursor = batch.get("next_cursor")
        if not isinstance(cursor, str) or not cursor:
            raise ValueError("Missing pagination cursor")
    else:
        raise ValueError("Pagination limit exceeded")
    text = "\n".join(
        fragment.get("plain_text", "")
        for block in blocks
        for fragment in block.get(block.get("type"), {}).get("rich_text", [])
    )
    return {"page_id": page_id, "text": text,
            "last_edited_at": page.get("last_edited_time"),
            "blocks_count": len(blocks)}, {
                "authenticated": True, "complete_inventory": True,
                "provider": "notion_rest"}
