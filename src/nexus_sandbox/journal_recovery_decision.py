"""Fail-closed recovery decision from a local journal observation.

This pure policy function cannot grant a worker lease, enable execution,
authenticate a host, or authorize an external write.
"""


def decide_recovery(readiness, *, exclusive_custody=False,
                    source_reobserved=False, effect_reconciled=False):
    if type(readiness) is not dict:
        raise ValueError("Explicit readiness evidence required")
    if (readiness.get("schema") != "nexus.journal.host-readiness.v1"
            or readiness.get("verdict") != "LOCAL_JOURNAL_OBSERVED_NOT_ACTIVATED"
            or type(readiness.get("journal")) is not dict
            or readiness["journal"].get("status") != "OBSERVED_EXISTING"
            or readiness["journal"].get("identity_match") is not True
            or readiness["journal"].get("integrity") != "ok"):
        return {"decision": "HOLD", "reason": "JOURNAL_NOT_VERIFIED"}
    if any(type(flag) is not bool for flag in (
            exclusive_custody, source_reobserved, effect_reconciled)):
        raise ValueError("Boolean evidence flags required")
    if not exclusive_custody:
        return {"decision": "HOLD", "reason": "EXCLUSIVE_CUSTODY_UNPROVEN"}
    if not source_reobserved:
        return {"decision": "HOLD", "reason": "SOURCE_NOT_REOBSERVED"}
    if not effect_reconciled:
        return {"decision": "OBSERVE_ONLY", "reason": "EFFECT_RECONCILIATION_REQUIRED"}
    return {
        "decision": "ELIGIBLE_FOR_BOUNDED_MANUAL_REVIEW",
        "reason": "NO_AUTOMATIC_WRITE_AUTHORIZATION",
    }
