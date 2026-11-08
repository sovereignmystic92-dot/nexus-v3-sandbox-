"""CP05 evidence gate: live identity, authorization and readback are separate facts."""
import re
from .csf_v02 import CSFValidationError

HEX = re.compile(r"^[0-9a-f]{64}$")
def assess_cp05(evidence):
    required = {"binding_sha256", "runner_principal", "destination_owner",
                "permission_verified", "write_attempted", "write_succeeded",
                "readback_matched", "source_link_verified", "idempotency_verified"}
    if not isinstance(evidence, dict) or set(evidence) != required:
        raise CSFValidationError("invalid CP05 evidence envelope")
    if not isinstance(evidence["binding_sha256"], str) or not HEX.fullmatch(evidence["binding_sha256"]):
        raise CSFValidationError("invalid binding digest")
    for field in ("runner_principal", "destination_owner"):
        if not isinstance(evidence[field], str) or not evidence[field].strip():
            raise CSFValidationError("missing principal or owner")
    for field in required - {"binding_sha256", "runner_principal", "destination_owner"}:
        if type(evidence[field]) is not bool:
            raise CSFValidationError("invalid evidence flag")
    if evidence["write_succeeded"] and not evidence["write_attempted"]:
        raise CSFValidationError("write evidence inconsistent")
    if evidence["readback_matched"] and not evidence["write_succeeded"]:
        raise CSFValidationError("readback evidence inconsistent")
    complete = all(evidence[k] for k in (
        "permission_verified", "write_attempted", "write_succeeded",
        "readback_matched", "source_link_verified", "idempotency_verified"))
    return {"status":"CP05_EVIDENCE_COMPLETE" if complete else "CP05_EVIDENCE_INCOMPLETE",
            "binding_sha256":evidence["binding_sha256"],
            "identity_recorded":True, "permission_verified":evidence["permission_verified"],
            "write_readback_verified":evidence["readback_matched"],
            "audit_gate_promoted":False}
