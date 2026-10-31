"""Strict provider observation envelope for a future trusted ChatGPT adapter.

This code validates a caller-supplied envelope. It does NOT authenticate a
connector, its user, the data, or a signature; none of the supplied fields are
attestations. Full source text and private analyses must not enter public CI.
"""
from dataclasses import dataclass
import re

DIGEST = re.compile(r"^[a-f0-9]{64}$")
SOURCE_FIELDS = frozenset({"provider","record_id","revision","content_sha256",
                            "complete","truncated","readback_kind"})
BINDING_FIELDS = frozenset({"transaction_id","source","output",
                             "independent_readback","authority_evidence"})
ID = re.compile(r"^[A-Za-z0-9:_.\\/-]{1,256}$")

@dataclass(frozen=True)
class EnvelopeVerdict:
    status: str
    next_action: str
    authenticated: bool = False
    write_authorized: bool = False
    cp09: str = "NOT_PROVEN"


def inspect_observation(record, expected_provider):
    if type(record) is not dict or set(record) != SOURCE_FIELDS:
        return "INVALID_OBSERVATION"
    if record["provider"] != expected_provider:
        return "WRONG_PROVIDER"
    if any(type(record[k]) is not str or
           not ID.fullmatch(record[k]) for k in
           ("record_id","revision","readback_kind")):
        return "INVALID_RECORD_IDENTITY"
    if type(record["content_sha256"]) is not str or not DIGEST.fullmatch(record["content_sha256"]):
        return "INVALID_CONTENT_DIGEST"
    if (type(record["complete"]) is not bool or
            type(record["truncated"]) is not bool):
        return "INVALID_COMPLETENESS_FLAGS"
    if not record["complete"] or record["truncated"]:
        return "INCOMPLETE_PROVIDER_OBSERVATION"
    if record["readback_kind"] != "FRESH_INDEPENDENT_FETCH":
        return "UNVERIFIED_READBACK_KIND"
    return None


def inspect_envelope(envelope):
    """Fail closed: data shape can be checked; provider authentication cannot."""
    def held(reason):
        return EnvelopeVerdict("HELD",reason)
    if type(envelope) is not dict or set(envelope) != BINDING_FIELDS:
        return held("INVALID_ENVELOPE")
    if type(envelope["transaction_id"]) is not str or not ID.fullmatch(envelope["transaction_id"]):
        return held("INVALID_TRANSACTION_ID")
    for field, provider in (("source","NOTION"),("output","CORTEX")):
        reason = inspect_observation(envelope[field],provider)
        if reason:
            return held(field.upper()+"_"+reason)
    if type(envelope["independent_readback"]) is not bool:
        return held("INVALID_INDEPENDENCE_FLAG")
    if not envelope["independent_readback"]:
        return held("INDEPENDENT_READBACK_NOT_ASSERTED")
    # No connector-issued signed attestations are supported in this version.
    # This field must explicitly be null; never accept self-proclaimed proof.
    if envelope["authority_evidence"] is not None:
        return held("AUTHORITY_NOT_AUTHENTICATED")
    return EnvelopeVerdict("UNAUTHENTICATED_ENVELOPE_VALID",
        "REQUIRE_TRUSTED_PROVIDER_AUTHORITY_AND_HOST_ENFORCEMENT")
