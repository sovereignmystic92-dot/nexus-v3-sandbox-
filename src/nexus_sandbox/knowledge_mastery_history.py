"""Pure historical knowledge reconciliation; never changes constitutional authority.

All historical revisions remain available for audit. A candidate supersession
requires explicit evidence and a trusted, externally supplied active revision.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class ReconciliationDecision:
    status: str
    reason: str
    effective_id: str | None = None
    preserved_ids: tuple[str, ...] = ()
    provider_writes: int = 0
    constitutional_changes: int = 0

def reconcile_history(*, records, active_constitution_revision):
    if type(records) not in (list, tuple) or not isinstance(active_constitution_revision, str) or not active_constitution_revision:
        return ReconciliationDecision("BLOCKED", "INVALID_INPUT")
    if not records:
        return ReconciliationDecision("BLOCKED", "NO_RECORDS")
    required = {"record_id", "revision", "supersedes", "source_refs", "evidence_refs",
                "constitution_revision", "review_independence_status", "contradiction_refs"}
    ids = set()
    by_id = {}
    for r in records:
        if type(r) is not dict or not required.issubset(r):
            return ReconciliationDecision("BLOCKED", "MISSING_PROVENANCE")
        rid = r["record_id"]
        if not isinstance(rid, str) or not rid or rid in ids:
            return ReconciliationDecision("BLOCKED", "DUPLICATE_OR_INVALID_ID")
        ids.add(rid)
        by_id[rid] = r
        if any(type(r[k]) is not list for k in ("supersedes", "source_refs", "evidence_refs", "contradiction_refs")):
            return ReconciliationDecision("BLOCKED", "INVALID_REFERENCES")
        if any(type(x) is not str or not x for k in ("supersedes", "source_refs", "evidence_refs", "contradiction_refs") for x in r[k]):
            return ReconciliationDecision("BLOCKED", "INVALID_REFERENCES")
        if not r["source_refs"] or not r["evidence_refs"]:
            return ReconciliationDecision("BLOCKED", "MISSING_EVIDENCE")
        if r["contradiction_refs"]:
            return ReconciliationDecision("BLOCKED", "UNRESOLVED_CONTRADICTION")
        if r["review_independence_status"] != "verified":
            return ReconciliationDecision("BLOCKED", "INDEPENDENT_REVIEW_REQUIRED")
        if r["constitution_revision"] != active_constitution_revision:
            return ReconciliationDecision("BLOCKED", "STALE_CONSTITUTION")
        if type(r["revision"]) is not int or r["revision"] < 1:
            return ReconciliationDecision("BLOCKED", "INVALID_REVISION")
        if len(set(r["supersedes"])) != len(r["supersedes"]):
            return ReconciliationDecision("BLOCKED", "DUPLICATE_SUPERSESSION")
    for r in records:
        for old in r["supersedes"]:
            if old not in by_id or old == r["record_id"]:
                return ReconciliationDecision("BLOCKED", "INVALID_SUPERSESSION_TARGET")
            if by_id[old]["revision"] >= r["revision"]:
                return ReconciliationDecision("BLOCKED", "NONMONOTONIC_REVISION")
    superseded = {old for r in records for old in r["supersedes"]}
    heads = [r for r in records if r["record_id"] not in superseded]
    if len(heads) != 1:
        return ReconciliationDecision("REVIEW_REQUIRED", "AMBIGUOUS_ACTIVE_HISTORY",
                                      preserved_ids=tuple(sorted(ids)))
    return ReconciliationDecision("CANDIDATE_ONLY", "REQUIRES_EXTERNAL_PROMOTION_GATE",
                                  effective_id=heads[0]["record_id"],
                                  preserved_ids=tuple(sorted(ids)))
