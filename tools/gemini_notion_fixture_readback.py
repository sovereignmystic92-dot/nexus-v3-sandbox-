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
from nexus_sandbox.notion_checkpoint_api import NotionRequest, NotionCheckpointAPI

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
    page = NotionCheckpointAPI(FIXTURE_ID, bounded, write_enabled=False).fetch_page(FIXTURE_ID)
    if page["id"] != FIXTURE_ID or page["truncated"] or page["unknown_block_count"]:
        raise ValueError("Incomplete fixture inventory")
    return {"result": "FIXTURE_READ_ONLY_OBSERVED",
            "fixture_id": FIXTURE_ID,
            "inventory_sha256": hashlib.sha256(page["text"].encode("utf-8")).hexdigest(),
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
