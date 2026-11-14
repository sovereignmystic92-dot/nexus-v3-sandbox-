"""Offline normalization of untrusted Dot proposals into Nexus event receipts.

No Dot API, credentials, network access, readiness advancement, or provider writes.
The adapter only creates a candidate envelope for the existing evaluator.
"""
from datetime import datetime, timezone
import hashlib
import json
from urllib.parse import urlsplit

MODULES = frozenset(("skill_forge", "personal_growth_forge", "field_journal",
                     "civilization_engine", "trading_platform"))
REPO = "sovereignmystic92-dot/nexus-v3-sandbox-"
SCHEMA = "dot_nexus_event_v1"
MAX_BYTES = 32768


def normalize(proposal):
    if not isinstance(proposal, dict):
        raise ValueError("proposal must be an object")
    try:
        raw = json.dumps(proposal, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid JSON proposal") from exc
    if len(raw.encode("utf-8")) > MAX_BYTES:
        raise ValueError("proposal exceeds size limit")
    if proposal.get("schema_version") != SCHEMA:
        raise ValueError("unsupported schema")
    origin = proposal.get("origin")
    if not isinstance(origin, dict) or origin.get("kind") != "dot":
        raise ValueError("invalid origin")
    agent = origin.get("agent_id")
    if not isinstance(agent, str) or not (1 <= len(agent) <= 128) or not agent.strip():
        raise ValueError("missing agent identity hint")
    # Claimed agent ID is NOT authentication.
    for field in ("event_id", "subject", "idempotency_key"):
        val = proposal.get(field)
        if not isinstance(val, str) or not val.strip() or len(val) > 512:
            raise ValueError("invalid " + field)
    if proposal.get("proposed_action") != "review":
        raise ValueError("only review proposals are supported")
    if proposal.get("evidence_status") != "UNVERIFIED":
        raise ValueError("unverified evidence required")
    modules = proposal.get("module_hints")
    if not isinstance(modules, list) or not modules or any(
            not isinstance(m, str) or m not in MODULES for m in modules):
        raise ValueError("invalid module routing")
    stamp = proposal.get("observed_at")
    if not isinstance(stamp, str):
        raise ValueError("missing observation time")
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid observation time") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    refs = proposal.get("source_refs")
    if not isinstance(refs, list) or not (1 <= len(refs) <= 16):
        raise ValueError("source references required")
    for ref in refs:
        if not isinstance(ref, dict):
            raise ValueError("invalid source reference")
        uri = ref.get("uri")
        if not isinstance(uri, str) or len(uri) > 2048:
            raise ValueError("invalid source URI")
        parts = urlsplit(uri)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise ValueError("source URI must be public-style HTTPS")
        digest = ref.get("sha256")
        if digest is not None and (not isinstance(digest, str) or len(digest) != 64
                                   or any(c not in "0123456789abcdef" for c in digest)):
            raise ValueError("invalid source digest")
    # Stable identity binds a repeated idempotency key to the same event key.
    # The full payload digest is separately retained so changed replays fail closed.
    identity = hashlib.sha256(json.dumps([agent, proposal["idempotency_key"]], separators=(",", ":")).encode("utf-8")).hexdigest()
    proposal_digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return {
        "repository": REPO,
        "event": "issues",
        "event_id": "dot:" + agent + ":" + proposal["idempotency_key"],
        "subject": identity,
        "proposal_digest": proposal_digest,
        "source_url": refs[0]["uri"],
        "module_hints": sorted(set(modules)),
    }
