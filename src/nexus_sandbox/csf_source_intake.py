"""Generic offline source-bound transcript preparation; no external calls or writes."""
import hashlib
import re
from .csf_v02 import CSFValidationError
from .csf_transcript_ingest import segment_transcript_bounded
from .csf_extractive_proposals import propose_excerpts
from .csf_review_packet import prepare_review_packet

def prepare_source(transcript, *, document_id, expected_sha256):
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise CSFValidationError("explicit lowercase SHA-256 pin required")
    if not isinstance(transcript, str):
        raise CSFValidationError("transcript must be text")
    digest = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
    if digest != expected_sha256:
        raise CSFValidationError("source fingerprint mismatch")
    bounded = segment_transcript_bounded(document_id, transcript)
    extraction = propose_excerpts(transcript, bounded)
    packet = prepare_review_packet(transcript, bounded, extraction)
    return {"document_id": document_id, "source_digest": digest,
            "segment_count": bounded["segment_count"],
            "proposal_count": extraction["proposal_count"],
            "review_item_count": packet["review_item_count"],
            "provider_called": False, "external_writes": 0,
            "approved_for_persistence": False, "audit_gate_promoted": False,
            "classification_performed": False}
