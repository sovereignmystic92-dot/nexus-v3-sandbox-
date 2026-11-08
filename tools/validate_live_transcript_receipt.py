#!/usr/bin/env python3
"""Fail-closed validation of a redacted real-transcript execution receipt.

No provider access. Does not establish that an execution actually happened.
"""
import json
import re
import sys

SHA256 = re.compile(r"^[0-9a-f]{64}$")
RUN_ID = re.compile(r"^[1-9][0-9]*$")
REQUIRED = ("schema", "event_id", "source_ref", "source_sha256", "source_byte_count",
            "idempotency_key", "github_run_id", "github_run_attempt", "policy_version",
            "authorization", "notion_source_id", "cortex_module_id",
            "source_readback", "output_readback", "duplicate_creations")
ALLOWED = set(REQUIRED) | {"status", "error_code"}
SCHEMA = "NEXUS_LIVE_TRANSCRIPT_RECEIPT_V1"

def validate(data):
    if not isinstance(data, dict):
        raise ValueError("receipt must be an object")
    missing = set(REQUIRED) - set(data)
    unknown = set(data) - ALLOWED
    if missing or unknown:
        raise ValueError("missing/unknown fields: %s / %s" % (sorted(missing), sorted(unknown)))
    if data["schema"] != SCHEMA:
        raise ValueError("unsupported schema")
    for key in ("event_id", "source_ref", "idempotency_key", "policy_version",
                "notion_source_id", "cortex_module_id"):
        if not isinstance(data[key], str) or not data[key].strip() or len(data[key]) > 512:
            raise ValueError("invalid " + key)
    if not isinstance(data["source_sha256"], str) or not SHA256.fullmatch(data["source_sha256"]):
        raise ValueError("invalid source hash")
    if type(data["source_byte_count"]) is not int or data["source_byte_count"] <= 0:
        raise ValueError("invalid source byte count")
    if not RUN_ID.fullmatch(str(data["github_run_id"])) or type(data["github_run_id"]) is bool:
        raise ValueError("invalid run id")
    if type(data["github_run_attempt"]) is not int or data["github_run_attempt"] < 1:
        raise ValueError("invalid attempt")
    if data["authorization"] not in ("ALLOW", "DENY"):
        raise ValueError("invalid authorization")
    for key in ("source_readback", "output_readback"):
        if type(data[key]) is not bool:
            raise ValueError("invalid " + key)
    if type(data["duplicate_creations"]) is not int or data["duplicate_creations"] < 0:
        raise ValueError("invalid duplicate count")
    if data.get("status") not in (None, "PASS", "BLOCKED", "FAIL"):
        raise ValueError("invalid status")
    if data.get("status") == "PASS" and not (
        data["authorization"] == "ALLOW" and data["source_readback"] and
        data["output_readback"] and data["duplicate_creations"] == 0
    ):
        raise ValueError("PASS contradicts evidence")
    return data

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: validate_live_transcript_receipt.py RECEIPT.json")
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            validate(json.load(f))
    except (OSError, ValueError, TypeError) as e:
        sys.exit("BLOCKED: " + str(e))
    print("Receipt schema valid; external claims NOT independently verified")
