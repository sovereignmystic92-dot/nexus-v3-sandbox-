"""ChatGPT<->GitHub synthetic two-stage adapter evidence gate.

No provider access, issue identity verification, credential authentication,
write authority, remote fencing, or action dispatch is implemented here.
A PRECHECK is review evidence, NEVER permission to execute a provider write.
"""
import hashlib
import json
import re
from dataclasses import dataclass

SHA = re.compile(r"^[0-9a-f]{64}$")
ID = re.compile(r"^[A-Za-z0-9:_./-]{1,256}$")
FIELDS = frozenset({"schema","transaction_id","source_store","source_id",
    "source_revision","source_sha256","output_store","output_id",
    "output_revision","intended_output_sha256","policy_revision","mode"})
RECEIPT = frozenset({"schema","transaction_id","intent_sha256",
    "source_sha256","output_id","output_revision",
    "observed_output_sha256","complete_readback","host_authority_verified"})


@dataclass(frozen=True)
class HandshakeDecision:
    status: str
    next_action: str
    intent_sha256: str | None = None
    provider_writes: int = 0
    automatic_execution: bool = False
    cp09: str = "NOT_PROVEN"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def precheck(intent):
    """Validates synthetic exact-route intent; NEVER grants a write."""
    def hold(reason):
        return HandshakeDecision("HELD", reason)
    if type(intent) is not dict or set(intent) != FIELDS:
        return hold("INVALID_INTENT_SCHEMA")
    if any(type(v) is not str for v in intent.values()):
        return hold("INVALID_INTENT_VALUES")
    if (intent["schema"] != "NEXUS_CHAT_GITHUB_HANDSHAKE_V1"
            or intent["mode"] != "SYNTHETIC_NO_WRITE"
            or intent["source_store"] != "NOTION"
            or intent["output_store"] != "CORTEX"):
        return hold("REJECT_ROUTE_OR_MODE")
    for key in ("transaction_id","source_id","source_revision","output_id",
                "output_revision","policy_revision"):
        if not ID.fullmatch(intent[key]):
            return hold("INVALID_IDENTITY")
    for key in ("source_sha256","intended_output_sha256"):
        if not SHA.fullmatch(intent[key]):
            return hold("INVALID_DIGEST")
    return HandshakeDecision("PRECHECK_VALIDATED",
                             "NO_PROVIDER_WRITE; AWAIT_SYNTHETIC_RECEIPT",
                             hashlib.sha256(canonical(intent)).hexdigest())


def postcheck(intent, receipt):
    """Verify matching synthetic readback assertions without calling providers."""
    pre = precheck(intent)
    if pre.status != "PRECHECK_VALIDATED":
        return pre
    def hold(reason):
        return HandshakeDecision("HELD",reason,pre.intent_sha256)
    if type(receipt) is not dict or set(receipt) != RECEIPT:
        return hold("INVALID_RECEIPT_SCHEMA")
    if any(type(v) is not str for k,v in receipt.items()
           if k not in ("complete_readback","host_authority_verified")):
        return hold("INVALID_RECEIPT_VALUES")
    if (type(receipt["complete_readback"]) is not bool or
            type(receipt["host_authority_verified"]) is not bool):
        return hold("INVALID_HOST_ASSERTIONS")
    if (receipt["schema"] != "NEXUS_CHAT_GITHUB_RECEIPT_V1"
            or receipt["transaction_id"] != intent["transaction_id"]
            or receipt["intent_sha256"] != pre.intent_sha256
            or receipt["source_sha256"] != intent["source_sha256"]
            or receipt["output_id"] != intent["output_id"]
            or receipt["output_revision"] != intent["output_revision"]):
        return hold("RECONCILE_RECEIPT_BINDING")
    if not receipt["complete_readback"]:
        return hold("READBACK_INCOMPLETE_NO_RETRY")
    if not receipt["host_authority_verified"]:
        return hold("HOST_AUTHORITY_UNVERIFIED")
    if receipt["observed_output_sha256"] != intent["intended_output_sha256"]:
        return hold("OUTPUT_MISMATCH_NO_RETRY")
    return HandshakeDecision("SYNTHETIC_RECEIPT_MATCHED",
                             "REVIEW_PROVIDER_ATTESTATION_BEFORE_LIVE_USE",
                             pre.intent_sha256)
