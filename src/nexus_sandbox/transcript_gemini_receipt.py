"""Fail-closed, content-free receipt for live Gemini transcript review.

Receipts carry correlation hashes and identity metadata only. They never
contain source text, review text, API keys, or authorization tokens.
"""
import hashlib
import json
from datetime import datetime, timezone

REQUIRED = ("event_id", "source_sha256", "review_sha256", "model",
            "provider_response_id", "status")


def make_receipt(result, *, workflow_run_id, workflow_run_attempt, commit_sha):
    if type(result) is not dict or result.get("status") != "GEMINI_REVIEW_OBTAINED_READ_ONLY":
        raise ValueError("successful read-only Gemini result required")
    for field in REQUIRED:
        value = result.get(field)
        if type(value) is not str or not value.strip():
            raise ValueError("missing receipt field: " + field)
    for field in ("source_sha256", "review_sha256"):
        digest = result[field]
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid SHA-256: " + field)
    if result.get("notion_writes") != 0 or result.get("cortex_writes") != 0:
        raise ValueError("receipt only supports zero provider writes")
    if result.get("durable_receipt_verified") is not False:
        raise ValueError("unverified receipt state required")
    if type(workflow_run_id) is not str or not workflow_run_id.isdigit():
        raise ValueError("invalid workflow run id")
    if type(workflow_run_attempt) is not str or not workflow_run_attempt.isdigit():
        raise ValueError("invalid run attempt")
    if type(commit_sha) is not str or len(commit_sha) != 40 or any(c not in "0123456789abcdef" for c in commit_sha):
        raise ValueError("invalid commit SHA")
    receipt = {key: result[key] for key in REQUIRED}
    receipt.update(schema="NEXUS_GEMINI_REVIEW_RECEIPT_V1",
                   workflow_run_id=workflow_run_id,
                   workflow_run_attempt=workflow_run_attempt,
                   commit_sha=commit_sha,
                   notion_writes=0, cortex_writes=0,
                   durable_receipt_verified=False)
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    receipt["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    return receipt


def verify_receipt(receipt):
    if type(receipt) is not dict or receipt.get("schema") != "NEXUS_GEMINI_REVIEW_RECEIPT_V1":
        raise ValueError("wrong receipt schema")
    digest = receipt.get("receipt_sha256")
    if type(digest) is not str:
        raise ValueError("missing receipt checksum")
    payload = dict(receipt)
    del payload["receipt_sha256"]
    if set(payload) != set(REQUIRED) | {"schema", "workflow_run_id",
            "workflow_run_attempt", "commit_sha", "notion_writes",
            "cortex_writes", "durable_receipt_verified"}:
        raise ValueError("unexpected receipt fields")
    expected = make_receipt(payload, workflow_run_id=payload["workflow_run_id"],
                            workflow_run_attempt=payload["workflow_run_attempt"],
                            commit_sha=payload["commit_sha"])
    if expected != receipt:
        raise ValueError("receipt mismatch")
    return True


def verify_expected_receipt(receipt, *, event_id, source_sha256,
                            workflow_run_id, workflow_run_attempt, commit_sha):
    """Verify integrity and caller-bound context, not provider authentication."""
    verify_receipt(receipt)
    expected = dict(event_id=event_id, source_sha256=source_sha256,
                    workflow_run_id=workflow_run_id,
                    workflow_run_attempt=workflow_run_attempt, commit_sha=commit_sha)
    for key, value in expected.items():
        if type(value) is not str or not value.strip() or receipt[key] != value:
            raise ValueError("receipt context mismatch: " + key)
    return True
