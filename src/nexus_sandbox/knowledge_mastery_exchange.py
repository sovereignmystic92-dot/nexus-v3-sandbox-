"""Offline, non-authoritative cross-module learning exchange.

Shares evidence-linked candidates, never credentials, grants, or policies.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class ExchangeDecision:
    status: str
    reason: str
    recipients: tuple[str, ...] = ()
    provider_writes: int = 0

def prepare_exchange(*, candidate, recipient_modules, active_constitution_revision):
    if type(candidate) is not dict or type(recipient_modules) not in (list, tuple):
        return ExchangeDecision("BLOCKED", "INVALID_INPUT")
    required = {"subject_id", "source_refs", "evidence_refs", "evaluation_ids",
                "constitution_revision", "contradiction_refs", "mastery_level"}
    if not required.issubset(candidate):
        return ExchangeDecision("BLOCKED", "MISSING_PROVENANCE")
    if candidate["constitution_revision"] != active_constitution_revision or not active_constitution_revision:
        return ExchangeDecision("BLOCKED", "STALE_CONSTITUTION")
    if candidate["contradiction_refs"]:
        return ExchangeDecision("BLOCKED", "UNRESOLVED_CONTRADICTION")
    if any(not isinstance(candidate[k], list) or not candidate[k] for k in
           ("source_refs", "evidence_refs", "evaluation_ids")):
        return ExchangeDecision("BLOCKED", "MISSING_EVIDENCE")
    if type(candidate["mastery_level"]) is not int or not 1 <= candidate["mastery_level"] <= 6:
        return ExchangeDecision("BLOCKED", "INVALID_MASTERY")
    forbidden = {"permissions", "credentials", "grants", "policy_override", "constitutional_change"}
    if forbidden.intersection(candidate):
        return ExchangeDecision("BLOCKED", "AUTHORITY_BOUNDARY")
    if not isinstance(candidate["subject_id"], str) or not candidate["subject_id"]:
        return ExchangeDecision("BLOCKED", "INVALID_SUBJECT")
    if any(type(x) is not str or not x for k in ("source_refs","evidence_refs","evaluation_ids") for x in candidate[k]):
        return ExchangeDecision("BLOCKED", "INVALID_EVIDENCE")
    if len(set(candidate["source_refs"])) != len(candidate["source_refs"]):
        return ExchangeDecision("BLOCKED", "DUPLICATE_SOURCE")
    if any(type(m) is not str or not m for m in recipient_modules):
        return ExchangeDecision("BLOCKED", "INVALID_RECIPIENT")
    recipients = tuple(sorted(set(recipient_modules)))
    if not recipients:
        return ExchangeDecision("BLOCKED", "NO_RECIPIENTS")
    return ExchangeDecision("CANDIDATE_READY_FOR_REVIEW", "NO_AUTOMATIC_PROMOTION", recipients)
