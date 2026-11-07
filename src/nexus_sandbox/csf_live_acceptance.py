"""Strict metadata-only receipt for manually authorized CSF Gemini acceptance.

A receipt proves a provider response passed the context-only contract. It does
not prove independent corroboration, persistence, or audit-gate closure.
"""
import json
import re

from .csf_v02 import CSFValidationError

EXPECTED_SOURCE = "2f8ba596e3d4672f412487981390de6f3357a5a7156aefbc73a98cc42abcd646"
EXPECTED_STATUS = "GEMINI_CONTEXT_REVIEW_VALIDATED"
REQUIRED_FALSE = (
    "approved_for_persistence", "audit_gate_promoted", "external_corroboration",
    "factual_verification",
)


def validate_live_acceptance_result(result, *, run_id, commit_sha):
    if not isinstance(result, dict):
        raise CSFValidationError("invalid acceptance result")
    if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
        raise CSFValidationError("invalid run identity")
    if not isinstance(commit_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        raise CSFValidationError("invalid commit identity")
    if (result.get("status") != EXPECTED_STATUS
            or result.get("source_digest") != EXPECTED_SOURCE
            or result.get("review_count") != 12
            or type(result.get("review_count")) is not int
            or result.get("provider_called") is not True
            or type(result.get("external_writes")) is not int
            or result["external_writes"] != 0
            or any(result.get(key) is not False for key in REQUIRED_FALSE)):
        raise CSFValidationError("live acceptance conditions not satisfied")
    return {
        "schema": "csf-gemini-live-acceptance-v1",
        "run_id": run_id,
        "commit_sha": commit_sha,
        "source_digest": EXPECTED_SOURCE,
        "review_count": 12,
        "status": "ACCEPTED_CONTEXT_ONLY",
        "provider_called": True,
        "external_writes": 0,
        "factual_verification": False,
        "approved_for_persistence": False,
        "audit_gate_promoted": False,
    }


def receipt_json(result, *, run_id, commit_sha):
    return json.dumps(validate_live_acceptance_result(
        result, run_id=run_id, commit_sha=commit_sha), sort_keys=True)
