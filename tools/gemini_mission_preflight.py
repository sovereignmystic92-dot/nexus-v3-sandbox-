"""Fail-closed preparation for a bounded Gemini review mission.

No network, credentials, provider invocation, or persistent writes.
"""
import hashlib
import json
from pathlib import Path

MISSION_ISSUE = 291
SOURCE_SHA256 = "3e08e40c1a500f638cbd67297d10e0c355b2281f1df66b9125b88a049c68cb41"
CLAIM_IDS = ("mr-001", "mr-002", "mr-003", "mr-004", "mr-005")

def prepare_mission(*, issue_number, manifest_path, source_bytes=None,
                    live_call_authorized=False, cost_confirmed=False):
    if type(issue_number) is not int or issue_number != MISSION_ISSUE:
        return {"status": "BLOCKED", "reason": "UNAPPROVED_MISSION", "provider_calls": 0}
    if live_call_authorized or cost_confirmed:
        return {"status": "BLOCKED", "reason": "LIVE_DISPATCH_NOT_IMPLEMENTED", "provider_calls": 0}
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "BLOCKED", "reason": "MANIFEST_UNAVAILABLE", "provider_calls": 0}
    claims = manifest.get("claims")
    if (manifest.get("source_sha256") != SOURCE_SHA256
            or manifest.get("source_bytes") != 19000
            or type(claims) is not list
            or tuple(c.get("claim_id") for c in claims if type(c) is dict) != CLAIM_IDS
            or len(claims) != len(CLAIM_IDS)
            or manifest.get("mastery_promoted") is not False
            or manifest.get("provider_writes") != 0):
        return {"status": "BLOCKED", "reason": "MANIFEST_BINDING_MISMATCH", "provider_calls": 0}
    if source_bytes is None:
        source_status = "SOURCE_NOT_INDEPENDENTLY_VERIFIED"
    elif type(source_bytes) is not bytes or len(source_bytes) != 19000 or hashlib.sha256(source_bytes).hexdigest() != SOURCE_SHA256:
        return {"status": "BLOCKED", "reason": "SOURCE_DIGEST_MISMATCH", "provider_calls": 0}
    else:
        source_status = "SOURCE_BYTES_VERIFIED"
        for c in claims:
            a, b = c.get("byte_start"), c.get("byte_end")
            if type(a) is not int or type(b) is not int or not 0 <= a < b <= len(source_bytes):
                return {"status": "BLOCKED", "reason": "INVALID_EVIDENCE_OFFSET", "provider_calls": 0}
            if source_bytes[a:b] != c.get("evidence_quote", "").encode("utf-8"):
                return {"status": "BLOCKED", "reason": "EVIDENCE_SPAN_MISMATCH", "provider_calls": 0}
    return {
        "status": "PREPARED_NOT_DISPATCHED",
        "issue_number": MISSION_ISSUE,
        "source_sha256": SOURCE_SHA256,
        "source_status": source_status,
        "claim_ids": list(CLAIM_IDS),
        "required_verdicts": ["ACCEPT_AS_ATTRIBUTED", "REVISE", "REJECT", "BLOCKED"],
        "reviewer": "Gemini (not yet invoked)",
        "provider_calls": 0,
        "provider_writes": 0,
        "mastery_promoted": False,
        "next_action": "AUTHORIZE_AND_VERIFY_LIVE_REVIEW_BRIDGE_SEPARATELY",
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    result = prepare_mission(issue_number=args.issue, manifest_path=args.manifest)
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PREPARED_NOT_DISPATCHED" else 1)
