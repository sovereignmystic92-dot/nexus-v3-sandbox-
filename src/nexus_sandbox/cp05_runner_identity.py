"""Fail-closed runner identity evidence, independent of workflow-supplied labels.

No credential exchange, provider calls, write permissions, or audit promotion.
"""
import re
from .csf_v02 import CSFValidationError

def validate_runner_identity(*, observed, expected):
    required = {"provider", "principal_id", "installation_id", "owner_id"}
    if not isinstance(observed, dict) or not isinstance(expected, dict):
        raise CSFValidationError("identity evidence required")
    if set(observed) != required or set(expected) != required:
        raise CSFValidationError("identity fields mismatch")
    for record in (observed, expected):
        if record["provider"] != "socra":
            raise CSFValidationError("unexpected provider")
        for key in required - {"provider"}:
            value = record[key]
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
                raise CSFValidationError("invalid identity field")
    if observed != expected:
        raise CSFValidationError("runner installation identity mismatch")
    return {"status": "CP05_RUNNER_IDENTITY_MATCHED_OFFLINE",
            "provider": "socra", "identity_matched": True,
            "provider_attestation_verified": False,
            "permission_verified": False, "external_writes": 0,
            "audit_gate_promoted": False}
