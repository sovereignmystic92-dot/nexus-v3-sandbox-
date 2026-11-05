"""Fail-closed validation of a CP05 read-only receipt; no network or provider writes.

This validates shape and fixture bindings, not host authentication or Notion
revision locking. An independent reviewer must verify run provenance separately.
"""
import hashlib
import json
import sys

PAGE = "40e8c067-daa4-8199-9f12-c9b6486de444"
MODULE = "module_01m6kzebbfdk4ptbsg88gsf0ja"
PAYLOAD = "The copper lantern stays lit at dawn."
ALLOWED = {"NOT_ATTESTED", "SOURCE_MATCHED", "BLOCKED"}


def validate(receipt):
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be object")
    required = ("schema", "mode", "attestation", "notion_page_id",
                "cortex_module_id", "fixture_payload_sha256", "provider_writes",
                "github_run_id", "github_job_id", "source_last_edited_at")
    if any(k not in receipt for k in required):
        raise ValueError("missing required receipt field")
    if receipt["schema"] != "NEXUS_CP05_SUPERVISED_READ_V1":
        raise ValueError("unexpected schema")
    if receipt["mode"] != "READ_ONLY" or receipt["provider_writes"] != 0:
        raise ValueError("not a zero-write observation")
    if receipt["attestation"] not in ALLOWED:
        raise ValueError("unearned authentication claim")
    if receipt["notion_page_id"] != PAGE or receipt["cortex_module_id"] != MODULE:
        raise ValueError("source/destination binding mismatch")
    if receipt["fixture_payload_sha256"] != hashlib.sha256(PAYLOAD.encode()).hexdigest():
        raise ValueError("fixture digest mismatch")
    for key in ("github_run_id", "github_job_id"):
        if not isinstance(receipt[key], int) or receipt[key] <= 0:
            raise ValueError("missing host run identity")
    if not isinstance(receipt["source_last_edited_at"], str) or not receipt["source_last_edited_at"].endswith("Z"):
        raise ValueError("source revision timestamp missing")
    return True


if __name__ == "__main__":
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            validate(json.load(f))
    except (IndexError, OSError, ValueError, TypeError) as exc:
        print("CP05 receipt BLOCKED:", type(exc).__name__)
        sys.exit(1)
    print("CP05 receipt shape and synthetic bindings VALID; host attestation NOT established")
