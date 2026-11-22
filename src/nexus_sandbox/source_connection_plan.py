"""Offline shared intake plan for knowledge development and CSF.

No dispatcher, provider effects, journal, receipt verification or promotion.
The plan is metadata, not an execution receipt or authorization.
"""
import hashlib
import json
import re
import uuid

from .csf_notional_intake import prepare_source_receipt


SCHEMA = "nexus.source-connection-plan.v1"
CONSUMERS = ("knowledge_development", "csf")


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode("utf-8")).hexdigest()


def _text(value):
    return type(value) is str and bool(value.strip()) and value == value.strip()


def prepare_connection_plan(source_envelope, *, mission_id, code_revision,
                            policy_revision):
    """Prepare deterministic metadata from the existing CSF source envelope.

    Source equality and local digest validation do not authenticate Notion.
    Replays reproduce keys only; the trusted host must reconcile retained
    receipts and uncertain intents before dispatching any downstream work.
    """
    if not _text(mission_id) or not _text(policy_revision):
        raise ValueError("explicit mission and policy revision required")
    if type(code_revision) is not str or not re.fullmatch(r"[0-9a-f]{40}", code_revision):
        raise ValueError("pinned implementation commit required")
    source = prepare_source_receipt(source_envelope)
    # Tighten identity for this plan without changing the existing intake API.
    document_id = source["document_id"]
    if not document_id.startswith("notion:"):
        raise ValueError("Notion page identity required")
    try:
        page_id = uuid.UUID(document_id.removeprefix("notion:"))
    except ValueError:
        raise ValueError("Notion page identity required") from None
    if document_id != "notion:" + str(page_id):
        raise ValueError("canonical Notion document ID required")
    if source["source_url"] != "https://app.notion.com/p/" + page_id.hex:
        raise ValueError("Notion source URL and document identity must match")
    if not _text(source["source_revision"]):
        raise ValueError("canonical source revision required")
    reference = {"document_id": document_id,
                 "source_url": source["source_url"],
                 "source_revision": source["source_revision"],
                 "source_sha256": source["content_digest"]}
    return _make_plan(reference, mission_id=mission_id,
                      code_revision=code_revision, policy_revision=policy_revision)


def validate_connection_plan(plan):
    """Validate a retained, unchanged preparation plan; this is not authentication."""
    if type(plan) is not dict or type(plan.get("source")) is not dict:
        raise ValueError("connection plan required")
    source = plan["source"]
    fields = {"document_id", "source_url", "source_revision", "source_sha256"}
    if set(source) != fields or not all(_text(value) for value in source.values()):
        raise ValueError("exact source reference required")
    try:
        page = uuid.UUID(source["document_id"].removeprefix("notion:"))
    except ValueError:
        raise ValueError("canonical Notion identity required") from None
    if (source["document_id"] != "notion:" + str(page)
            or source["source_url"] != "https://app.notion.com/p/" + page.hex
            or not re.fullmatch(r"[0-9a-f]{64}", source["source_sha256"])):
        raise ValueError("source reference mismatch")
    if (not _text(plan.get("mission_id")) or not _text(plan.get("policy_revision"))
            or type(plan.get("code_revision")) is not str
            or not re.fullmatch(r"[0-9a-f]{40}", plan["code_revision"])):
        raise ValueError("pinned mission, code and policy required")
    expected = _make_plan(source, mission_id=plan["mission_id"],
                          code_revision=plan["code_revision"],
                          policy_revision=plan["policy_revision"])
    # Canonical serialization also distinguishes bools from numeric flags.
    if json.dumps(plan, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True):
        raise ValueError("connection plan changed; reconcile before execution")


def _make_plan(reference, *, mission_id, code_revision, policy_revision):
    source_key = _digest({"schema": SCHEMA, "source": reference})
    binding = {"schema": SCHEMA, "source_key": source_key,
               "mission_id": mission_id, "code_revision": code_revision,
               "policy_revision": policy_revision}
    plan_id = _digest(binding)
    return {**binding, "plan_id": plan_id, "source": reference,
            "status": "PLAN_ONLY",
            "source_integrity_status": "LOCAL_DIGEST_MATCHED_NOT_AUTHENTICATED",
            "next_action": "AUTHENTICATE_SOURCE_AND_RECONCILE_EXISTING_RECEIPTS",
            "consumers": [
                {"consumer": consumer, "source_key": source_key,
                 "work_key": _digest({"plan_id": plan_id, "consumer": consumer}),
                 "status": "NOT_STARTED", "receipt_ref": None}
                for consumer in CONSUMERS],
            "provider_called": False, "external_writes": 0,
            "approved_for_persistence": False, "audit_gate_promoted": False}
