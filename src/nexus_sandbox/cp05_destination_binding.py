"""CP05 offline destination binding preflight. No network or persistence."""
import hashlib
import re
from .csf_v02 import CSFValidationError

_HEX = re.compile(r"^[0-9a-f]{64}$")
_UUID = re.compile(r"^[0-9a-f]{32}$")
def validate_binding(source, destination, *, approved=False):
    if not isinstance(source, dict) or not isinstance(destination, dict):
        raise CSFValidationError("source and destination required")
    if set(source) != {"notion_page_id", "source_revision", "source_sha256"}:
        raise CSFValidationError("invalid source binding")
    page = source["notion_page_id"]
    if not isinstance(page, str) or not _UUID.fullmatch(page.replace("-", "")):
        raise CSFValidationError("invalid source page")
    if not isinstance(source["source_revision"], str) or not source["source_revision"].strip():
        raise CSFValidationError("missing source revision")
    if not isinstance(source["source_sha256"], str) or not _HEX.fullmatch(source["source_sha256"]):
        raise CSFValidationError("invalid source digest")
    if set(destination) != {"system", "project_id", "object_type"}:
        raise CSFValidationError("invalid destination binding")
    if destination["system"] != "cortex" or destination["object_type"] != "derived_output":
        raise CSFValidationError("unauthorized destination")
    project = destination["project_id"]
    if not isinstance(project, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", project):
        raise CSFValidationError("invalid project identifier")
    if approved is not False:
        raise CSFValidationError("offline preflight cannot authorize writes")
    identity = "|".join((page.replace("-", ""), source["source_revision"],
                         source["source_sha256"], project, destination["object_type"]))
    return {"status":"CP05_BINDING_PREFLIGHT_ONLY",
            "binding_sha256":hashlib.sha256(identity.encode("utf-8")).hexdigest(),
            "source_sha256":source["source_sha256"],
            "destination_system":"cortex", "provider_called":False,
            "destination_principal_verified":False,
            "destination_readback_verified":False,
            "external_writes":0, "audit_gate_promoted":False}
