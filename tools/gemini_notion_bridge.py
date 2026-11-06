"""Fail-closed validation for proposed Gemini -> Notion synthetic metadata updates.

This stage does not send provider requests or modify Notion.
"""
import hashlib
import json
import re
import sys

FIXTURE_ID = "40e8c067daa481999f12c9b6486de444"
MARKER = "NXS-GEMINI-NOTION-SYNTHETIC-V1"
ALLOWED_KEYS = {"schema_version", "page_id", "marker", "summary"}
SAFE_SUMMARY = re.compile(r"[A-Za-z0-9 .,;:()_-]{1,160}\Z")
MAX_BYTES = 1024


def validate(raw):
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_BYTES:
        raise ValueError("Invalid payload size")
    obj = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    if type(obj) is not dict or set(obj) != ALLOWED_KEYS:
        raise ValueError("Unexpected schema")
    if type(obj["schema_version"]) is not int or obj["schema_version"] != 1:
        raise ValueError("Unsupported version")
    if type(obj["page_id"]) is not str or obj["page_id"].replace("-", "") != FIXTURE_ID:
        raise ValueError("Unapproved destination")
    if type(obj["marker"]) is not str or obj["marker"] != MARKER:
        raise ValueError("Unexpected marker")
    if type(obj["summary"]) is not str or not SAFE_SUMMARY.fullmatch(obj["summary"]):
        raise ValueError("Unsafe summary")
    return {"schema_version": 1, "page_id": FIXTURE_ID,
            "marker": MARKER, "summary": obj["summary"]}


def _reject_duplicate_keys(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("Duplicate JSON key")
        out[key] = value
    return out


def main():
    try:
        raw = sys.stdin.read(MAX_BYTES + 1)
        result = validate(raw)
        digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        print(json.dumps({"result": "VALIDATED_DRY_RUN", "sha256": digest,
                          "writes_attempted": 0, "notion_readback": "NOT_TESTED"}))
        return 0
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        print('{"result":"BLOCKED","writes_attempted":0}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
