"""Offline CP05 receipt bridge: validate two schemas without claiming host attestation."""
import hashlib
import json
import sys
from datetime import datetime
from cp05_supervised_receipt_verify import validate as validate_supervised, PAGE

SOURCE_SCHEMA = "NEXUS_CP05_NOTION_SOURCE_SNAPSHOT_V1"
EXPECTED_JOB = "notion-fixture"
EXPECTED_PAYLOAD = "The copper lantern stays lit at dawn."

def _utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("source revision must be UTC")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid source revision") from exc

def validate_source(source):
    if not isinstance(source, dict):
        raise ValueError("source receipt must be object")
    if source.get("schema") != SOURCE_SCHEMA or source.get("mode") != "READ_ONLY":
        raise ValueError("source schema or mode mismatch")
    if source.get("notion_page_id") != PAGE or source.get("github_job_name") != EXPECTED_JOB:
        raise ValueError("source identity mismatch")
    if type(source.get("github_run_id")) is not int or source["github_run_id"] <= 0:
        raise ValueError("missing run identity")
    if type(source.get("provider_writes")) is not int or source["provider_writes"] != 0:
        raise ValueError("nonzero or unverified writes")
    if source.get("checkpoint") != "NOT_ATTESTED" or source.get("cortex_host_auth") != "NOT_ATTESTED":
        raise ValueError("unearned source attestation")
    if type(source.get("block_count")) is not int or source["block_count"] < 1:
        raise ValueError("invalid block count")
    for field in ("canonical_inventory_sha256", "fixture_payload_sha256"):
        digest = source.get(field)
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid digest")
    _utc(source.get("source_revision"))
    return True

def bridge(source, supervised):
    validate_source(source)
    validate_supervised(supervised)
    if supervised["attestation"] != "NOT_ATTESTED":
        raise ValueError("offline bridge cannot promote attestation")
    if source["github_run_id"] != supervised["github_run_id"]:
        raise ValueError("run identity mismatch")
    if source["source_revision"] != supervised["source_last_edited_at"]:
        raise ValueError("source revision mismatch")
    if source["notion_page_id"] != supervised["notion_page_id"]:
        raise ValueError("page mismatch")
    # The supervised schema hashes the phrase alone; source schema hashes the
    # complete extracted text. Never equate these different digests.
    if supervised["fixture_payload_sha256"] != hashlib.sha256(EXPECTED_PAYLOAD.encode()).hexdigest():
        raise ValueError("fixture phrase mismatch")
    return {"result": "SHAPE_AND_BINDINGS_MATCHED", "checkpoint": "NOT_ATTESTED",
            "host_provenance": "NOT_VERIFIED", "cortex_host_auth": "NOT_ATTESTED",
            "source_inventory_verified_independently": False,
            "provider_writes": 0, "github_run_id": source["github_run_id"]}

if __name__ == "__main__":
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            source = json.load(f)
        with open(sys.argv[2], encoding="utf-8") as f:
            supervised = json.load(f)
        print(json.dumps(bridge(source, supervised), sort_keys=True))
    except (IndexError, OSError, ValueError, TypeError, KeyError) as exc:
        print("CP05 bridge BLOCKED:", type(exc).__name__)
        sys.exit(1)
