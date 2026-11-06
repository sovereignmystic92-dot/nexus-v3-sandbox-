"""Read-only, exact-target Notion fixture observation for bridge #154.

Never sends PATCH/POST or includes provider content in its output.
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from urllib.parse import urlencode
from uuid import UUID
from nexus_sandbox.notion_checkpoint_api import NotionRequest
from nexus_sandbox.notion_inventory import observe

FIXTURE_ID = "40e8c067daa481999f12c9b6486de444"


def observe_fixture(request):
    reads = 0
    def bounded(method, path, payload):
        nonlocal reads
        if method != "GET" or payload is not None:
            raise ValueError("Read-only observation")
        reads += 1
        if reads > 22:
            raise ValueError("Read budget exceeded")
        return request(method, path, payload)
    page = bounded("GET", "/v1/pages/" + FIXTURE_ID, None)
    if (type(page) is not dict or page.get("object") != "page"
            or UUID(page["id"]).hex != FIXTURE_ID
            or page.get("archived") is not False or page.get("in_trash") is not False):
        raise ValueError("Unavailable or mismatched fixture page")
    def children(parent_id, query):
        return bounded("GET", "/v1/blocks/" + parent_id + "/children?" + urlencode(query), None)
    root, inventory = observe(FIXTURE_ID, children, max_pages=10)
    fragments = []
    for block in root:
        kind = block["type"]
        if kind in {"paragraph", "heading_1", "heading_2", "heading_3",
                    "bulleted_list_item", "numbered_list_item", "quote",
                    "callout", "to_do", "toggle", "code"}:
            for item in block[kind]["rich_text"]:
                if item["type"] == "text":
                    fragments.append(item["plain_text"])
    content = "\\n".join(fragments)
    if "The copper lantern stays lit at dawn." not in content:
        raise ValueError("Expected synthetic fixture phrase absent")
    return {"result": "FIXTURE_CONTENT_MATCHED_READ_ONLY",
            "fixture_id": FIXTURE_ID,
            "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "blocks_observed": inventory["blocks_observed"],
            "read_requests": reads, "writes_attempted": 0}


def main():
    if (os.environ.get("GITHUB_REPOSITORY") != "sovereignmystic92-dot/nexus-v3-sandbox-"
            or os.environ.get("GITHUB_REF") != "refs/heads/main"
            or os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
            or os.environ.get("NOTION_BRIDGE_READ_CONFIRMED") != "true"
            or re.fullmatch(r"[1-9][0-9]*", os.environ.get("GITHUB_RUN_ATTEMPT", "")) is None):
        print('{"result":"BLOCKED_CONTEXT","writes_attempted":0}')
        return 2
    try:
        token = os.environ.pop("NOTION_SANDBOX_TOKEN", "")
        request = NotionRequest(FIXTURE_ID, token, "2022-06-28", write_enabled=False)
        result = observe_fixture(request)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        print('{"result":"BLOCKED_OBSERVATION","writes_attempted":0}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
