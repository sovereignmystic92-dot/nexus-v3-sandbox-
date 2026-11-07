"""Credential-free validation of Nexus transcript receipts; not provider attestation."""
import json
import re
import sys

HEX = re.compile(r"[0-9a-f]{64}\Z")
FIELDS = {"schema_version", "status", "trigger", "source", "notion", "cortex", "run_id"}
PROVIDER = {"object_id", "write_ok", "readback_ok", "sha256"}

def validate(r):
    if not isinstance(r, dict) or set(r) != FIELDS or r["schema_version"] != 1:
        raise ValueError("invalid schema")
    if r["status"] not in ("BLOCKED", "INCOMPLETE", "VERIFIED"):
        raise ValueError("invalid status")
    if r["trigger"] not in ("schedule", "repository_dispatch", "workflow_dispatch", "issues", "manual_connector"):
        raise ValueError("invalid trigger")
    if not isinstance(r["run_id"], str) or not r["run_id"]:
        raise ValueError("missing run ID")
    s = r["source"]
    if not isinstance(s, dict) or set(s) != {"id", "sha256", "bytes"}:
        raise ValueError("invalid source")
    if not isinstance(s["id"], str) or not s["id"] or type(s["bytes"]) is not int or s["bytes"] <= 0 or not isinstance(s["sha256"], str) or not HEX.fullmatch(s["sha256"]):
        raise ValueError("invalid source evidence")
    for p in ("notion", "cortex"):
        e = r[p]
        if not isinstance(e, dict) or set(e) != PROVIDER:
            raise ValueError("invalid provider evidence")
        if not isinstance(e["object_id"], str) or not e["object_id"] or not isinstance(e["sha256"], str) or not HEX.fullmatch(e["sha256"]):
            raise ValueError("invalid provider identifiers/hash")
        if type(e["write_ok"]) is not bool or type(e["readback_ok"]) is not bool or (e["readback_ok"] and not e["write_ok"]):
            raise ValueError("invalid provider verification")
    if r["status"] == "VERIFIED":
        if r["trigger"] == "manual_connector" or not all(r[p]["write_ok"] and r[p]["readback_ok"] for p in ("notion", "cortex")):
            raise ValueError("verified without automated provider readback")
        if r["notion"]["sha256"] != s["sha256"]:
            raise ValueError("source fidelity mismatch")
    return True

if __name__ == "__main__":
    try:
        validate(json.load(sys.stdin))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        sys.exit("BLOCKED: " + str(exc))
    print("STRUCTURE VALID; provider evidence not independently attested")
