"""Fail-closed source-grounded review packet for an independent reviewer.

Local preparation only: no model calls, no network and no persistence.
A reviewer's response is not automatically a verified factual finding.
"""
import hashlib
from .csf_v02 import CSFValidationError


def prepare_review_packet(transcript, bounded, extraction, max_context_chars=1600):
    if not isinstance(transcript, str) or not isinstance(bounded, dict) or not isinstance(extraction, dict):
        raise CSFValidationError("invalid review input")
    if type(max_context_chars) is not int or not 1 <= max_context_chars <= 5000:
        raise CSFValidationError("invalid context limit")
    digest = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
    if bounded.get("content_digest") != digest or extraction.get("source_digest") != digest:
        raise CSFValidationError("source digest mismatch")
    spans = bounded.get("spans")
    proposals = extraction.get("proposals")
    if not isinstance(spans, dict) or not isinstance(proposals, list):
        raise CSFValidationError("missing evidence inventory")
    position = 0
    for sid, span in spans.items():
        if not isinstance(sid, str) or not isinstance(span, dict):
            raise CSFValidationError("invalid segment")
        start, end = span.get("start"), span.get("end")
        if type(start) is not int or type(end) is not int or start != position or end <= start or end > len(transcript):
            raise CSFValidationError("noncontiguous segment")
        if hashlib.sha256(transcript[start:end].encode("utf-8")).hexdigest() != span.get("sha256"):
            raise CSFValidationError("segment integrity failure")
        position = end
    if position != len(transcript) or bounded.get("segment_count") != len(spans):
        raise CSFValidationError("incomplete segment coverage")
    if extraction.get("proposal_count") != len(proposals) or extraction.get("classification_performed") is not False or extraction.get("external_writes") != 0:
        raise CSFValidationError("unreviewed proposal contract violated")
    seen = set()
    items = []
    for proposal in proposals:
        if not isinstance(proposal, dict):
            raise CSFValidationError("invalid proposal")
        sid, start, end = proposal.get("segment_id"), proposal.get("start"), proposal.get("end")
        if sid not in spans or type(start) is not int or type(end) is not int or (sid, start, end) in seen:
            raise CSFValidationError("invalid or duplicate proposal reference")
        span = spans[sid]
        if not (span["start"] <= start < end <= span["end"]):
            raise CSFValidationError("proposal outside segment")
        excerpt = transcript[start:end]
        if hashlib.sha256(excerpt.encode("utf-8")).hexdigest() != proposal.get("excerpt_sha256") or proposal.get("review_status") != "unverified_source_statement":
            raise CSFValidationError("proposal provenance mismatch")
        seen.add((sid, start, end))
        context_start = max(span["start"], start - max_context_chars // 2)
        context_end = min(span["end"], end + max_context_chars // 2)
        if context_end - context_start > max_context_chars:
            context_end = min(context_end, context_start + max_context_chars)
        items.append({"segment_id": sid, "start": start, "end": end,
                      "excerpt": excerpt, "context": transcript[context_start:context_end],
                      "context_start": context_start, "context_end": context_end,
                      "excerpt_sha256": proposal["excerpt_sha256"],
                      "status": "pending_independent_review"})
    return {"source_digest": digest, "segment_count": len(spans),
            "review_items": items, "review_item_count": len(items),
            "instructions": "Distinguish what the transcript says from independent verification. Flag unsupported, ambiguous, or context-dependent statements. Do not assume source claims are true.",
            "provider_called": False, "external_writes": 0, "audit_gate_promoted": False}
