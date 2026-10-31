"""Read-only bridge from observed provider metadata to Nexus receipt gates.

Requires a trusted host to fetch provider records and calculate content digests.
No secret, transcript or analysis bytes need be sent to GitHub. A syntactically
valid manifest is NOT proof of origin, access rights or write authorization.
"""
from dataclasses import dataclass
from .provider_evidence_envelope import inspect_envelope
from .provider_custody import valid_intent, digest

@dataclass(frozen=True)
class BindingResult:
    status: str
    next_action: str
    intent_sha256: str | None = None
    authenticated: bool = False
    write_authorized: bool = False
    provider_writes: int = 0
    cp09: str = "NOT_PROVEN"

def assess_existing_records(intent, envelope):
    """Compare two independently supplied observations without side effects.

    Refuse all incomplete, self-declared-authorization or mismatching records.
    Successful comparison remains an unauthenticated review candidate.
    """
    def hold(reason):
        return BindingResult("HELD", reason)
    if not valid_intent(intent):
        return hold("INVALID_CUSTODY_INTENT")
    verdict = inspect_envelope(envelope)
    if verdict.status != "UNAUTHENTICATED_ENVELOPE_VALID":
        return hold(verdict.next_action)
    if envelope["transaction_id"] != intent["transaction_id"]:
        return hold("TRANSACTION_ID_MISMATCH")
    for record, prefix in ((envelope["source"], "notion"),
                           (envelope["output"], "cortex")):
        if (record["record_id"] != intent[prefix + ("_source_id" if prefix=="notion" else "_output_id")]
            or record["revision"] != intent[prefix + "_revision"]
            or record["content_sha256"] != intent[prefix + "_sha256"]):
            return hold(prefix.upper() + "_IDENTITY_OR_CONTENT_MISMATCH")
    return BindingResult("UNAUTHENTICATED_BINDING_MATCHED",
                         "REQUIRE_INDEPENDENT_PROVIDER_AUTHENTICATION",
                         digest(intent))
