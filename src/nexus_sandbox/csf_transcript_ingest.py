"""Offline CSF transcript segmentation and evidence-bound candidate ingestion.

No language model, network, persistence or automatic factual classification.
"""
import hashlib
import re

from .csf_v02 import CSFValidationError, deduplicate, make_finding, validate_finding

MAX_TRANSCRIPT_CHARS = 2_000_000


def segment_transcript(document_id, transcript):
    """Split a supplied, nonempty transcript into stable numbered paragraphs.

    Exact input bytes determine content_digest; callers must retain the original
    transcript in the authorized source archive. This does not verify provenance.
    """
    if not isinstance(document_id, str) or not document_id.strip():
        raise CSFValidationError("document_id required")
    if not isinstance(transcript, str) or not transcript.strip() or len(transcript) > MAX_TRANSCRIPT_CHARS:
        raise CSFValidationError("transcript missing or oversized")
    digest = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
    chunks = [part.strip() for part in re.split(r"\n\s*\n", transcript) if part.strip()]
    segments = {f"seg-{i:04d}": part for i, part in enumerate(chunks, 1)}
    return {"document_id": document_id, "content_digest": digest, "segments": segments}


def ingest_candidates(source, candidates):
    """Produce findings from explicitly supplied candidate annotations.

    Each candidate must have segment_id, assertion, domain_id, claim_type,
    systemic_role, confidence_level and confidence_rationale. Causal links
    are optional, but every evidence reference must resolve to source segments.
    """
    if not isinstance(source, dict) or set(source) != {"document_id", "content_digest", "segments"}:
        raise CSFValidationError("invalid source envelope")
    segments = source["segments"]
    if not isinstance(segments, dict) or not segments or not all(
        isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in segments.items()
    ):
        raise CSFValidationError("invalid segments")
    # Reconstructing the digest from segments is unsafe because whitespace was
    # normalized by segmentation; provenance must be verified at source intake.
    if not isinstance(candidates, list):
        raise CSFValidationError("candidate list required")
    records = []
    allowed = {"segment_id", "assertion", "domain_id", "claim_type",
               "systemic_role", "confidence_level", "confidence_rationale", "causal_links"}
    required = allowed - {"causal_links"}
    for candidate in candidates:
        if not isinstance(candidate, dict) or not required <= set(candidate) or not set(candidate) <= allowed:
            raise CSFValidationError("invalid candidate shape")
        sid = candidate["segment_id"]
        if not isinstance(sid, str) or sid not in segments:
            raise CSFValidationError("candidate references unknown segment")
        record = make_finding(
            source["document_id"], sid, segments[sid], candidate["assertion"],
            candidate["domain_id"], candidate["claim_type"], candidate["systemic_role"],
            content_digest=source["content_digest"], causal_links=candidate.get("causal_links", []),
            confidence_level=candidate["confidence_level"],
            confidence_rationale=candidate["confidence_rationale"],
        )
        validate_finding(record, segments)
        records.append(record)
    return deduplicate(records)
