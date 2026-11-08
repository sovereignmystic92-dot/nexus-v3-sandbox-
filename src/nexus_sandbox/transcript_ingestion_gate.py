"""Provider-neutral transcript ingestion gate. No network or write capability."""
from nexus_sandbox.transcript_fidelity import build_receipt, split_transcript, verify_readback


def prepare_transcript(raw, chunk_bytes=12000):
    """Return exact chunks and immutable-content receipt for a supplied source."""
    receipt = build_receipt(raw, chunk_bytes)
    return {"schema": "nexus.transcript-ingestion-gate.v1",
            "receipt": receipt, "chunks": split_transcript(raw, chunk_bytes),
            "state": "AWAITING_ARCHIVE_READBACK",
            "cortex_write_allowed": False, "audit_promotion": False}


def verify_archive(prepared, readback_chunks):
    """Fail closed; emit a non-authorizing verification decision."""
    if not isinstance(prepared, dict) or prepared.get("schema") != "nexus.transcript-ingestion-gate.v1":
        raise ValueError("invalid prepared ingestion")
    chunks, receipt = prepared.get("chunks"), prepared.get("receipt")
    if not isinstance(chunks, list) or not all(isinstance(x, str) for x in chunks):
        raise ValueError("missing original chunks")
    original = "".join(chunks)
    valid = (build_receipt(original, receipt.get("chunk_bytes")) == receipt
             and verify_readback(original, readback_chunks, receipt))
    return {"source_sha256": receipt["sha256"], "archive_readback_verified": bool(valid),
            "state": "ARCHIVE_VERIFIED" if valid else "BLOCKED_ARCHIVE_MISMATCH",
            "cortex_write_allowed": False, "audit_promotion": False,
            "next_step": "BOUNDED_DERIVED_REVIEW" if valid else None}



def plan_archive_resume(prepared, destination, observation, *, expected_source_sha256):
    """Plan a single-worker retry from a complete, fresh host readback.

    The host pins destination/source independently, authenticates and paginates
    the observation, and serializes writes. None means unknown outcome: read
    again, never blindly append. This pure planner grants no write authority.
    """
    if not isinstance(destination, str) or not destination.strip():
        raise ValueError("pinned destination required")
    if not isinstance(prepared, dict):
        raise ValueError("invalid prepared ingestion")
    receipt = prepared.get("receipt")
    chunks = prepared.get("chunks")
    if (not isinstance(receipt, dict) or not isinstance(chunks, list)
            or not chunks or not all(isinstance(c, str) for c in chunks)):
        raise ValueError("invalid prepared source")
    if type(receipt.get("chunk_bytes")) is not int:
        raise ValueError("invalid chunk size")
    if (prepared.get("schema") != "nexus.transcript-ingestion-gate.v1"
            or build_receipt("".join(chunks), receipt["chunk_bytes"]) != receipt
            or split_transcript("".join(chunks), receipt["chunk_bytes"]) != chunks
            or receipt.get("sha256") != expected_source_sha256):
        raise ValueError("source does not match pinned receipt")
    result = {"source_sha256": expected_source_sha256,
              "destination": destination, "missing_chunks": [],
              "archive_readback_verified": False,
              "provider_writes_allowed": False, "cortex_write_allowed": False,
              "audit_promotion": False}
    if observation is None:
        return dict(result, state="READBACK_REQUIRED")
    if (not isinstance(observation, dict)
            or observation.get("complete") is not True
            or observation.get("destination") != destination
            or observation.get("source_sha256") != expected_source_sha256
            or not isinstance(observation.get("chunks"), list)):
        raise ValueError("complete destination-bound readback required")
    seen, previous = set(), -1
    for item in observation["chunks"]:
        if not isinstance(item, dict):
            raise ValueError("invalid observed chunk")
        index = item.get("index")
        if (type(index) is not int or not 0 <= index < len(chunks)
                or index in seen or index <= previous
                or item.get("text") != chunks[index]):
            raise ValueError("conflicting, duplicate or unordered chunk")
        seen.add(index)
        previous = index
    missing = [{"index": i, "text": c} for i, c in enumerate(chunks) if i not in seen]
    if missing:
        return dict(result, state="MISSING_CHUNKS", missing_chunks=missing)
    # Preserve provider order rather than sorting away storage mistakes.
    verified = verify_archive(prepared, [c["text"] for c in observation["chunks"]])
    if not verified["archive_readback_verified"]:
        raise ValueError("full readback mismatch")
    return dict(result, state="ARCHIVE_VERIFIED", archive_readback_verified=True)
