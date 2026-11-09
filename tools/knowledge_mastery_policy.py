"""Pure, fail-closed Knowledge Mastery evaluation policy; no provider access."""
from collections import defaultdict

LEVELS = tuple(range(7))

def assess(receipts, *, subject_id, required_level=1):
    """Return a bounded assessment. Never grants permissions or writes knowledge."""
    if required_level not in LEVELS:
        raise ValueError("invalid mastery level")
    seen_ids = set()
    accepted = []
    blocked = []
    for record in receipts:
        if record.get("subject_id") != subject_id:
            continue
        eid = record.get("evaluation_id")
        if not isinstance(eid, str) or not eid or eid in seen_ids:
            blocked.append({"evaluation_id": eid, "reason": "missing_or_duplicate_id"})
            continue
        seen_ids.add(eid)
        if record.get("outcome") != "pass":
            blocked.append({"evaluation_id": eid, "reason": "not_passed"})
            continue
        if record.get("source_integrity_status") != "verified":
            blocked.append({"evaluation_id": eid, "reason": "unverified_source"})
            continue
        if record.get("review_independence_status") != "verified":
            blocked.append({"evaluation_id": eid, "reason": "review_not_independent"})
            continue
        if not record.get("evidence_refs") or not record.get("source_refs"):
            blocked.append({"evaluation_id": eid, "reason": "missing_evidence"})
            continue
        if record.get("contradiction_refs"):
            blocked.append({"evaluation_id": eid, "reason": "unresolved_contradiction"})
            continue
        level = record.get("mastery_level")
        if type(level) is not int or level not in LEVELS or level == 0:
            blocked.append({"evaluation_id": eid, "reason": "missing_level"})
            continue
        accepted.append(record)
    # Evidence is counted by independent source identity, never receipt volume.
    distinct_sources = set()
    supported = []
    for record in sorted(accepted, key=lambda r: (r["mastery_level"], r["evaluation_id"])):
        sources = set(record["source_refs"])
        if sources & distinct_sources:
            blocked.append({"evaluation_id": record["evaluation_id"], "reason": "dependent_source"})
            continue
        distinct_sources.update(sources)
        supported.append(record)
    level = max((r["mastery_level"] for r in supported), default=0)
    return {
        "subject_id": subject_id, "demonstrated_level": level,
        "meets_requested_level": level >= required_level,
        "accepted_evaluation_ids": [r["evaluation_id"] for r in supported],
        "blocked": blocked,
        "status": "candidate_only",  # not an authorized Cortex promotion
    }
