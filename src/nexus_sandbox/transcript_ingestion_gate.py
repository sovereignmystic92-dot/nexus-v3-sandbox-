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
