"""Deterministic, non-secret Chat -> Cortex handoff packet. Offline only."""
import hashlib
import json
import re

HEX = re.compile(r"^[a-f0-9]{64}$")
URL = re.compile(r"^https://github\.com/[^/\s]+/[^/\s]+/issues/[1-9][0-9]*$")
ALLOWED = {"source_issue_url", "source_sha256", "source_revision", "destination_module",
           "intent", "evidence_class", "actor", "scope", "approval_reference"}

def make_packet(fields):
    if not isinstance(fields, dict) or set(fields) != ALLOWED:
        raise ValueError("invalid packet keys")
    if not all(isinstance(v, str) and v.strip() and len(v) <= 512 for v in fields.values()):
        raise ValueError("invalid packet value")
    if not URL.fullmatch(fields["source_issue_url"]):
        raise ValueError("source must be a GitHub issue")
    if not HEX.fullmatch(fields["source_sha256"]):
        raise ValueError("invalid digest")
    if fields["actor"] != "chatgpt-connected-cortex":
        raise ValueError("actor must reflect actual connector")
    if fields["scope"] not in ("read-only", "single-module-write"):
        raise ValueError("scope not bounded")
    if fields["evidence_class"] not in ("operational-decision", "derived-knowledge", "synthetic-test"):
        raise ValueError("evidence class unsupported")
    canonical = json.dumps(fields, sort_keys=True, separators=(",", ":"))
    return {"schema": "nexus.chat-cortex.handoff.v1",
            "packet_id": hashlib.sha256(canonical.encode()).hexdigest(),
            "request": dict(fields),
            "execution_state": "PENDING_CHAT_REVIEW",
            "provider_authenticated_by_github": False,
            "cortex_write_verified": False,
            "audit_gate_promoted": False}

def validate_receipt(packet, receipt):
    if packet.get("schema") != "nexus.chat-cortex.handoff.v1":
        raise ValueError("schema mismatch")
    if not isinstance(receipt, dict) or receipt.get("packet_id") != packet.get("packet_id"):
        raise ValueError("receipt mismatch")
    if receipt.get("actor") != "chatgpt-connected-cortex":
        raise ValueError("wrong actor")
    if receipt.get("status") not in ("READBACK_VERIFIED", "BLOCKED", "READ_ONLY_COMPLETE"):
        raise ValueError("invalid status")
    if receipt.get("status") == "READBACK_VERIFIED":
        if packet["request"]["scope"] != "single-module-write" or not receipt.get("readback_matched"):
            raise ValueError("unverified write")
    if receipt.get("audit_gate_promoted") is not False:
        raise ValueError("audit promotion forbidden")
    return True
