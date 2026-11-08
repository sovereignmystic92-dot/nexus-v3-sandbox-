"""Fail-closed execution receipt classification at the host/runner boundary.

This does not authenticate providers or persist receipts. The runner must supply
independent, verified evidence before it may mark an execution complete.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class RunnerEvidence:
    authenticated_trigger: bool
    authenticated_notion: bool
    authenticated_cortex: bool
    durable_receipt_id: str
    receipt_readback_matches: bool


def classify_execution(handoff, evidence):
    """Return status without converting local provider readback into runner proof."""
    if type(evidence) is not RunnerEvidence:
        raise ValueError("runner evidence required")
    if handoff.status != "READBACK_MATCHED":
        return "BLOCKED"
    if any(type(x) is not bool for x in (
        evidence.authenticated_trigger, evidence.authenticated_notion,
        evidence.authenticated_cortex, evidence.receipt_readback_matches)):
        raise ValueError("invalid evidence flag")
    if not (evidence.authenticated_trigger and evidence.authenticated_notion
            and evidence.authenticated_cortex):
        return "INCOMPLETE"
    if not isinstance(evidence.durable_receipt_id, str) or not evidence.durable_receipt_id.strip():
        return "INCOMPLETE"
    if not evidence.receipt_readback_matches:
        return "INCOMPLETE"
    return "VERIFIED"
