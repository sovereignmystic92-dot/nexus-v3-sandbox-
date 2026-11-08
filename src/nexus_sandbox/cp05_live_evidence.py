"""CP05 evidence evaluation for standing-authorized Cortex operations.

A bounded grant may be reused without per-operation approval. This module never
issues a grant, performs writes, or promotes an audit gate.
"""
import re
from .csf_v02 import CSFValidationError

HEX = re.compile(r"^[0-9a-f]{64}$")
FIELDS = {"binding_sha256", "runner_principal", "destination_owner",
          "permission_verified", "write_attempted", "write_succeeded",
          "readback_matched", "source_link_verified", "idempotency_verified"}
GRANT_FIELDS = {"principal", "destination_owner", "binding_sha256",
                "read_allowed", "write_allowed", "active"}

def assess_cp05(evidence, *, standing_grant=None):
    if not isinstance(evidence, dict) or set(evidence) != FIELDS:
        raise CSFValidationError("invalid CP05 evidence envelope")
    if not isinstance(evidence["binding_sha256"], str) or not HEX.fullmatch(evidence["binding_sha256"]):
        raise CSFValidationError("invalid binding digest")
    for field in ("runner_principal", "destination_owner"):
        if not isinstance(evidence[field], str) or not evidence[field].strip():
            raise CSFValidationError("missing principal or owner")
    for field in FIELDS - {"binding_sha256", "runner_principal", "destination_owner"}:
        if type(evidence[field]) is not bool:
            raise CSFValidationError("invalid evidence flag")
    if evidence["write_succeeded"] and not evidence["write_attempted"]:
        raise CSFValidationError("write evidence inconsistent")
    if evidence["readback_matched"] and not evidence["write_succeeded"]:
        raise CSFValidationError("readback evidence inconsistent")
    grant_valid = False
    if standing_grant is not None:
        if not isinstance(standing_grant, dict) or set(standing_grant) != GRANT_FIELDS:
            raise CSFValidationError("invalid standing grant")
        for key in ("read_allowed", "write_allowed", "active"):
            if type(standing_grant[key]) is not bool:
                raise CSFValidationError("invalid grant permission")
        grant_valid = (standing_grant["active"] and standing_grant["read_allowed"]
                       and standing_grant["write_allowed"]
                       and standing_grant["principal"] == evidence["runner_principal"]
                       and standing_grant["destination_owner"] == evidence["destination_owner"]
                       and standing_grant["binding_sha256"] == evidence["binding_sha256"])
    verified = all(evidence[k] for k in (
        "permission_verified", "write_attempted", "write_succeeded",
        "readback_matched", "source_link_verified", "idempotency_verified"))
    return {"status":("CP05_EVIDENCE_COMPLETE" if verified and grant_valid
                      else "CP05_EVIDENCE_INCOMPLETE"),
            "binding_sha256":evidence["binding_sha256"],
            "standing_grant_matched":grant_valid,
            "permission_verified":evidence["permission_verified"],
            "write_readback_verified":evidence["readback_matched"],
            "requires_exception_review":not (verified and grant_valid),
            "audit_gate_promoted":False}
