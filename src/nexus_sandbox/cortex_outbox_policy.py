"""Content-free Cortex outbox proposal validation; NO network or provider writes."""
from dataclasses import dataclass
import re

HEX64 = re.compile(r"^[0-9a-f]{64}$")
OPERATIONS = frozenset({"create", "update"})
FIELDS = frozenset({"schema_version", "source_system", "source_id_hash", "source_digest",
                    "operation", "target_key_hash", "request_id", "status",
                    "evidence_refs", "created_at"})

class ProposalRejected(ValueError):
    pass

@dataclass(frozen=True)
class Decision:
    status: str
    reason: str

def validate_manifest(manifest):
    if not isinstance(manifest, dict) or set(manifest) != FIELDS:
        raise ProposalRejected("manifest fields mismatch")
    if manifest["schema_version"] != 1:
        raise ProposalRejected("unsupported schema")
    if manifest["source_system"] not in ("notion", "synthetic"):
        raise ProposalRejected("unapproved source")
    for field in ("source_id_hash", "source_digest", "target_key_hash"):
        if not isinstance(manifest[field], str) or not HEX64.fullmatch(manifest[field]):
            raise ProposalRejected("invalid digest")
    if manifest["operation"] not in OPERATIONS or manifest["status"] != "PREPARED":
        raise ProposalRejected("unsafe operation or status")
    if not isinstance(manifest["request_id"], str) or not re.fullmatch(r"[a-zA-Z0-9._:-]{1,128}", manifest["request_id"]):
        raise ProposalRejected("invalid request identifier")
    if not isinstance(manifest["created_at"], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", manifest["created_at"]):
        raise ProposalRejected("invalid timestamp")
    refs = manifest["evidence_refs"]
    if not isinstance(refs, list) or len(refs) > 8 or not all(isinstance(r, str) and re.fullmatch(r"[a-zA-Z0-9._:/#-]{1,160}", r) for r in refs):
        raise ProposalRejected("invalid evidence references")
    return Decision("PREPARED", "manifest validated; no provider operation performed")

def authorize_commit(*, identity_verified=False, grants_verified=False,
                     approved_scope=False, remote_fencing_verified=False,
                     exclusive_quiescent_gateway_verified=False):
    # A positive decision is still NOT a write. No transport is provided.
    if not (identity_verified and grants_verified and approved_scope):
        return Decision("BLOCKED", "identity/grants/scope not verified")
    if not (remote_fencing_verified or exclusive_quiescent_gateway_verified):
        return Decision("BLOCKED", "remote fencing or exclusive quiescent gateway not verified")
    return Decision("ELIGIBLE_FOR_SEPARATE_REVIEW", "no mutation performed")
