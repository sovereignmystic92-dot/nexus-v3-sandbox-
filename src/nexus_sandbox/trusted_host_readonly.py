"""Bounded read-only provider boundary for an independently operated Nexus host.

Credentials and transport are deliberately outside this module. The host must
instantiate authenticated provider clients and keep all source bytes private.
No network, provider writes, GitHub permissions or signed attestation here.
"""
from dataclasses import dataclass
import hashlib
from .provider_custody import valid_intent

@dataclass(frozen=True)
class ProbeDecision:
    status: str
    next_action: str
    provider_writes: int = 0
    write_authorized: bool = False
    cp09: str = "NOT_PROVEN"

def _digest(raw):
    if type(raw) is not bytes:
        raise ValueError("Provider returned non-byte payload")
    return hashlib.sha256(raw).hexdigest()

def observe_existing(intent, notion, cortex):
    """Read the two exact IDs and compare host-returned revision and bytes.

    Client interfaces must be provided by a separate trusted host:
      read_exact(id) -> {id, revision, content_bytes, complete, truncated}
      permissions_exact(id) -> {edit: bool, owner: bool}
    This only checks outcomes; cannot authenticate client implementations.
    """
    def hold(reason):
        return ProbeDecision("HELD",reason)
    if not valid_intent(intent):
        return hold("INVALID_INTENT")
    try:
        src=notion.read_exact(intent["notion_source_id"])
        out=cortex.read_exact(intent["cortex_output_id"])
        access=cortex.permissions_exact(intent["cortex_output_id"])
    except Exception:
        return hold("PROVIDER_READ_OR_PERMISSION_ERROR")
    for record, prefix in ((src,"notion"),(out,"cortex")):
        if type(record) is not dict or set(record)!={"id","revision","content_bytes","complete","truncated"}:
            return hold("INVALID_PROVIDER_RECORD")
        rid=intent[prefix+("_source_id" if prefix=="notion" else "_output_id")]
        if (record["id"]!=rid or record["revision"]!=intent[prefix+"_revision"] or
                type(record["complete"]) is not bool or record["complete"] is not True or
                type(record["truncated"]) is not bool or record["truncated"] is not False):
            return hold("INCOMPLETE_OR_STALE_PROVIDER_RECORD")
        try:
            observed=_digest(record["content_bytes"])
        except ValueError:
            return hold("INVALID_PROVIDER_BYTES")
        if observed!=intent[prefix+"_sha256"]:
            return hold("CONTENT_DIGEST_MISMATCH")
    if (type(access) is not dict or set(access)!={"edit","owner"}
            or type(access["edit"]) is not bool or type(access["owner"]) is not bool
            or not access["edit"] or not access["owner"]):
        return hold("INSUFFICIENT_CORTEX_PERMISSION_REPORT")
    return ProbeDecision("READ_ONLY_PROVIDER_SNAPSHOTS_MATCHED",
                         "REQUIRE_HOST_AUTHENTICATION_AND_REMOTE_FENCING")

