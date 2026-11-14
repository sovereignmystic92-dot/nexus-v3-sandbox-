import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

PAGE = "4188c067-daa4-8134-9cda-f30c901aa875"
REVISION = "2026-11-14T07:55:36.051Z"
DIGEST = "f2122b71e7762479e026c7f4614378526410f1560bd560e1eadc03d6f0d2e0c8"


def read_notion(path, token):
    request = Request("https://api.notion.com/v1/" + path, headers={
        "Authorization": "Bearer " + token,
        "Notion-Version": "2022-06-28",
    })
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def verify(page, children):
    if page.get("id") != PAGE or page.get("last_edited_time") != REVISION or children.get("has_more") is not False:
        raise ValueError("SOURCE_REVISION_OR_COVERAGE_MISMATCH")
    chunks = []
    pending = False
    expected_code = False
    for block in children["results"]:
        kind = block["type"]
        if block.get("has_children"):
            raise ValueError("UNEXPECTED_NESTED_BLOCK")
        value = "".join(item["plain_text"] for item in block[kind].get("rich_text", []))
        if expected_code:
            if kind != "code":
                raise ValueError("MISSING_RAW_CHUNK")
            chunks.append(value.encode("utf-8"))
            expected_code = False
        elif kind == "heading_2" and value.startswith("Raw chunk "):
            if value != f"Raw chunk {len(chunks)}":
                raise ValueError("RAW_CHUNK_ORDER_MISMATCH")
            expected_code = True
        elif kind == "paragraph" and value == "Transfer status: Pending Cortex Processing.":
            pending = True
        elif kind not in {"paragraph", "heading_2"}:
            raise ValueError("UNEXPECTED_BLOCK")
    raw = b"".join(chunks)
    if expected_code or not pending or len(chunks) != 4 or len(raw) != 21528 or hashlib.sha256(raw).hexdigest() != DIGEST:
        raise ValueError("SOURCE_FIDELITY_OR_STATUS_MISMATCH")


def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise SystemExit("NOTION_READ_CREDENTIAL_UNAVAILABLE")
    try:
        page = read_notion("pages/" + PAGE, token)
        children = read_notion("blocks/" + PAGE + "/children?page_size=100", token)
        verify(page, children)
        if read_notion("pages/" + PAGE, token).get("last_edited_time") != REVISION:
            raise ValueError("SOURCE_REVISION_CHANGED")
    except Exception as exc:
        code = str(exc) if type(exc) is ValueError and str(exc).isupper() else type(exc).__name__
        raise SystemExit("NOTION_SOURCE_BLOCKED: " + code) from None
    receipt = {
        "status": "SOURCE_READY", "source_id": PAGE, "source_revision": REVISION,
        "source_sha256": DIGEST, "source_bytes": 21528, "video_id": "bEjwo1yUK8c",
        "destination_module": f"Nexus Analysis — {PAGE} — {DIGEST}",
        "run_id": os.environ["GITHUB_RUN_ID"], "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "commit": os.environ["GITHUB_SHA"], "event": os.environ["GITHUB_EVENT_NAME"],
    }
    Path("source-ready.json").write_text(json.dumps(receipt) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
