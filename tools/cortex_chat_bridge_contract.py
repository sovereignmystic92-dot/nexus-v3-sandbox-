"""Offline, durable Cortex-through-Chat handoff contract.

No ChatGPT invocation, Cortex network access, or implied authorization.
Only an independently verified readback can close a handoff.
"""
import hashlib
import json

STATES = frozenset({"PREPARED", "READY_FOR_CHAT", "SUBMITTED",
                    "READBACK_VERIFIED", "COMPLETE", "RETRY_REQUIRED", "BLOCKED"})
TRANSITIONS = {
    "PREPARED": {"READY_FOR_CHAT", "BLOCKED"},
    "READY_FOR_CHAT": {"SUBMITTED", "BLOCKED"},
    "SUBMITTED": {"READBACK_VERIFIED", "RETRY_REQUIRED", "BLOCKED"},
    "READBACK_VERIFIED": {"COMPLETE", "BLOCKED"},
    "RETRY_REQUIRED": {"READY_FOR_CHAT", "BLOCKED"},
    "BLOCKED": set(),
    "COMPLETE": set(),
}


def _sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 2048


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def make_handoff(source, analysis, operation="upsert_analysis"):
    """Prepare a content-addressed request; keep raw transcripts in Notion."""
    if operation != "upsert_analysis":
        raise ValueError("unsupported Cortex operation")
    if not isinstance(source, dict) or not isinstance(analysis, dict):
        raise ValueError("source and analysis must be objects")
    for key in ("notion_page_id", "source_revision"):
        if not _nonempty(source.get(key)):
            raise ValueError("missing source reference: " + key)
    if not _sha(source.get("sha256")):
        raise ValueError("invalid source checksum")
    for key in ("analysis_id", "revision", "artifact_uri"):
        if not _nonempty(analysis.get(key)):
            raise ValueError("missing analysis reference: " + key)
    if not _sha(analysis.get("sha256")):
        raise ValueError("invalid analysis checksum")
    request = {"contract_version": "cortex_chat_bridge_v0.1.0",
               "operation": operation,
               "source": {key: source[key] for key in ("notion_page_id", "source_revision", "sha256")},
               "analysis": {key: analysis[key] for key in ("analysis_id", "revision", "artifact_uri", "sha256")}}
    key = hashlib.sha256(canonical(request).encode("utf-8")).hexdigest()
    return {"request": request, "idempotency_key": key, "state": "PREPARED",
            "receipts": [], "cortex_persisted": False, "readiness_advanced": False}


def advance(handoff, next_state, evidence=None):
    """Validate transitions; receipts are immutable append-only snapshots."""
    if not isinstance(handoff, dict) or handoff.get("state") not in STATES:
        raise ValueError("invalid handoff")
    if next_state not in TRANSITIONS[handoff["state"]]:
        raise ValueError("illegal handoff transition")
    if not _sha(handoff.get("idempotency_key")):
        raise ValueError("invalid handoff key")
    if not isinstance(handoff.get("receipts"), list):
        raise ValueError("invalid receipts")
    if next_state in ("SUBMITTED", "READBACK_VERIFIED", "RETRY_REQUIRED", "BLOCKED"):
        if not isinstance(evidence, dict) or not _nonempty(evidence.get("evidence_ref")):
            raise ValueError("evidence reference required")
    if next_state == "READBACK_VERIFIED":
        if not isinstance(evidence, dict) or evidence.get("verified") is not True:
            raise ValueError("independent readback verification required")
        if evidence.get("idempotency_key") != handoff["idempotency_key"]:
            raise ValueError("readback identity mismatch")
        if not _nonempty(evidence.get("cortex_record_id")):
            raise ValueError("Cortex record reference required")
        if evidence.get("source_sha256") != handoff["request"]["source"]["sha256"]:
            raise ValueError("source checksum mismatch")
        if evidence.get("analysis_sha256") != handoff["request"]["analysis"]["sha256"]:
            raise ValueError("analysis checksum mismatch")
    updated = dict(handoff)
    updated["receipts"] = list(handoff["receipts"]) + [{"from": handoff["state"],
        "to": next_state, "evidence": dict(evidence) if evidence is not None else None}]
    updated["state"] = next_state
    updated["cortex_persisted"] = next_state in ("READBACK_VERIFIED", "COMPLETE")
    updated["readiness_advanced"] = False
    return updated
