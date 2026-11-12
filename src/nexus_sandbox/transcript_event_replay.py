"""Offline event/replay contract for transcript ingestion. No provider I/O."""
import re

_HEX = re.compile(r"^[0-9a-f]{64}$")
_STEPS = ("source_verified", "archive_written", "archive_readback", "derived_written", "derived_readback")


def replay_transcript_events(events, source_sha256):
    """Replay an append-only event stream; fail closed on conflict or missing proof.

    Returns a synthetic state, never authorization to perform external writes.
    """
    if not isinstance(source_sha256, str) or not _HEX.fullmatch(source_sha256):
        raise ValueError("valid source digest required")
    if not isinstance(events, list):
        raise ValueError("event list required")
    seen = {}
    completed = []
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("invalid event")
        eid, step = event.get("event_id"), event.get("step")
        if not isinstance(eid, str) or not eid or step not in _STEPS:
            raise ValueError("invalid event identity or step")
        if event.get("source_sha256") != source_sha256:
            raise ValueError("source mismatch")
        if event.get("authorized") is not True or event.get("evidence") is not True:
            raise ValueError("authorization and evidence required")
        if eid in seen:
            if seen[eid] != event:
                raise ValueError("conflicting replay")
            continue
        seen[eid] = dict(event)
        if step in completed:
            raise ValueError("duplicate step with different identity")
        if step != _STEPS[len(completed)]:
            raise ValueError("out-of-order or missing proof")
        completed.append(step)
    return {"schema": "nexus.transcript-event-replay.v1",
            "source_sha256": source_sha256,
            "completed_steps": completed,
            "next_step": _STEPS[len(completed)] if len(completed) < len(_STEPS) else None,
            "status": "SYNTHETIC_COMPLETE" if len(completed) == len(_STEPS) else "SYNTHETIC_INCOMPLETE",
            "provider_writes": False, "audit_promotion": False}
