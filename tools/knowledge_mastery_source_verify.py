"""Verify a full-fidelity archived transcript before offline mastery evaluation.

This utility accepts an independently exported UTF-8 file. It never downloads
from Notion, grants authority, or writes to Cortex.
"""
import hashlib
import json
from pathlib import Path

MASS_RELAYS = {
    "source_id": "notion:4128c067-daa4-81fe-a010-fd3cc75575df",
    "title": "Mass Effect | The Truth About the Mass Relays",
    "byte_count": 19000,
    "sha256": "3e08e40c1a500f638cbd67297d10e0c355b2281f1df66b9125b88a049c68cb41",
    "chunks": (
        (12000, "2d5aedb8822b02ebaf532006ae5ec4fa043167ba45c673c79fbe391ed9b421ab"),
        (7000, "ffd4c4da8cf97d051440345fc9505d4bbad69d3781422a8ff0fc0bd9217e8235"),
    ),
}

def verify_source(data: bytes, manifest=MASS_RELAYS):
    """Fail closed on any byte, chunk-order, or digest mismatch."""
    if type(data) is not bytes:
        return {"status": "BLOCKED", "reason": "INVALID_INPUT"}
    try:
        data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return {"status": "BLOCKED", "reason": "INVALID_UTF8"}
    if len(data) != manifest["byte_count"]:
        return {"status": "BLOCKED", "reason": "BYTE_COUNT_MISMATCH"}
    if hashlib.sha256(data).hexdigest() != manifest["sha256"]:
        return {"status": "BLOCKED", "reason": "SOURCE_HASH_MISMATCH"}
    pos = 0
    for count, expected in manifest["chunks"]:
        chunk = data[pos:pos + count]
        if len(chunk) != count or hashlib.sha256(chunk).hexdigest() != expected:
            return {"status": "BLOCKED", "reason": "CHUNK_HASH_MISMATCH"}
        pos += count
    if pos != len(data):
        return {"status": "BLOCKED", "reason": "CHUNK_LENGTH_MISMATCH"}
    return {
        "status": "SOURCE_BYTES_VERIFIED",
        "source_id": manifest["source_id"],
        "source_sha256": manifest["sha256"],
        "byte_count": len(data),
        "next_action": "REQUIRE_INDEPENDENT_CLAIM_REVIEW",
        "mastery_promoted": False,
        "provider_writes": 0,
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Verify raw Mass Relays transcript bytes")
    parser.add_argument("raw_transcript", type=Path,
                        help="Raw UTF-8 source bytes only; no Markdown fences or separators")
    args = parser.parse_args()
    result = verify_source(args.raw_transcript.read_bytes())
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "SOURCE_BYTES_VERIFIED" else 1

if __name__ == "__main__":
    raise SystemExit(main())
