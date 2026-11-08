"""Read-only triage of locally supplied Chat-Cortex packets.

No network calls, provider access, or autonomous Chat invocation.
"""
import json
from nexus_sandbox.chat_cortex_handoff import ALLOWED, make_packet


def triage_packet(raw):
    """Return a non-authorizing triage decision; never execute a write."""
    try:
        obj = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(obj, dict):
            raise ValueError("packet is not an object")
        if obj.get("schema") != "nexus.chat-cortex.handoff.v1":
            raise ValueError("unsupported schema")
        req = obj.get("request")
        if not isinstance(req, dict) or set(req) != ALLOWED:
            raise ValueError("unsupported request")
        canonical = make_packet(req)
        if canonical["packet_id"] != obj.get("packet_id"):
            raise ValueError("packet integrity mismatch")
        if obj.get("execution_state") != "PENDING_CHAT_REVIEW":
            raise ValueError("not pending")
        if obj.get("provider_authenticated_by_github") is not False:
            raise ValueError("unverified GitHub auth claim")
        if obj.get("audit_gate_promoted") is not False:
            raise ValueError("audit promotion claim")
        if obj.get("cortex_write_verified") is not False:
            raise ValueError("unverified write claim")
        return {"packet_id": canonical["packet_id"], "decision": "REVIEW_REQUIRED",
                "scope": req["scope"], "source_issue_url": req["source_issue_url"],
                "destination_module": req["destination_module"],
                "authorization_verified": False, "provider_called": False,
                "audit_gate_promoted": False}
    except (ValueError, TypeError, KeyError):
        return {"decision": "BLOCKED_INVALID_PACKET", "authorization_verified": False,
                "provider_called": False, "audit_gate_promoted": False}


def triage_batch(items, limit=20):
    """Finite, deduplicated triage with no writes."""
    if not isinstance(items, list) or not isinstance(limit, int) or not 1 <= limit <= 20:
        raise ValueError("invalid batch")
    if len(items) > limit:
        raise ValueError("batch exceeds limit")
    seen = set()
    results = []
    for item in items:
        result = triage_packet(item)
        pid = result.get("packet_id")
        if pid in seen:
            results.append({"packet_id": pid, "decision": "DUPLICATE",
                            "authorization_verified": False, "provider_called": False,
                            "audit_gate_promoted": False})
        else:
            if pid:
                seen.add(pid)
            results.append(result)
    return results
