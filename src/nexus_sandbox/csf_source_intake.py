"""Generic offline source-bound transcript preparation; no external calls or writes."""
import hashlib
import re
from .csf_identity import _digest, bind_finding
from .csf_notional_intake import prepare_source_receipt
from .csf_v02 import CSFValidationError
from .csf_transcript_ingest import ingest_candidates, segment_transcript_bounded
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


def prepare_findings(source_envelope, assigned_candidates):
    """Build pending review payloads from the host's saved claim assignments.

    Pass a mapping of stable claim IDs to candidate annotations. The host must
    save the mapping before dispatch and reuse its keys on replay or rewording.
    Output contains derived text and belongs in restricted storage.
    """
    if not isinstance(assigned_candidates, dict) or not assigned_candidates:
        raise CSFValidationError("saved claim assignments required")
    if not isinstance(source_envelope, dict):
        raise CSFValidationError("source envelope required")

    source = prepare_source_receipt(source_envelope)
    transcript = source_envelope["transcript"]
    bounded = segment_transcript_bounded(source["document_id"], transcript)
    segments = {
        sid: transcript[span["start"]:span["end"]]
        for sid, span in bounded["spans"].items()
    }
    candidate_source = {
        "document_id": source["document_id"],
        "content_digest": source["content_digest"],
        "segments": segments,
    }
    if any(not isinstance(key, str) or not key or key != key.strip()
           for key in assigned_candidates):
        raise CSFValidationError("assigned claim ID required")

    return [
        bind_finding(
            source_envelope,
            ingest_candidates(candidate_source, [assigned_candidates[claim_id]])[0],
            claim_id=claim_id,
        )
        for claim_id in sorted(assigned_candidates)
    ]


def require_review_binding(prepared_finding, review):
    """Check association with a prepared finding. Provider evidence is separate."""
    if not isinstance(review, dict):
        raise CSFValidationError("review binding required")
    payload = prepared_finding["payload"]
    if (review.get("finding_id") != payload["finding_id"]
            or review.get("payload_sha256") != prepared_finding["payload_sha256"]
            or prepared_finding["payload_sha256"] != _digest(payload)):
        raise CSFValidationError("review does not match prepared finding")
