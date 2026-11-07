"""Deterministic, unverified source excerpts for human/independent review.

These are not factual findings or classifications. No provider or persistence.
"""
import hashlib
import re
from .csf_v02 import CSFValidationError


def propose_excerpts(transcript, bounded, limit=12):
    if not isinstance(transcript, str) or not isinstance(bounded, dict):
        raise CSFValidationError("invalid source")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise CSFValidationError("invalid proposal limit")
    digest = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
    if bounded.get("content_digest") != digest:
        raise CSFValidationError("source digest mismatch")
    spans = bounded.get("spans")
    if not isinstance(spans, dict) or not spans:
        raise CSFValidationError("missing source spans")
    position = 0
    proposals = []
    for sid, span in spans.items():
        if not isinstance(span, dict) or type(span.get("start")) is not int or type(span.get("end")) is not int:
            raise CSFValidationError("invalid span")
        start, end = span["start"], span["end"]
        if start != position or end <= start or end > len(transcript):
            raise CSFValidationError("noncontiguous source")
        piece = transcript[start:end]
        if hashlib.sha256(piece.encode("utf-8")).hexdigest() != span.get("sha256"):
            raise CSFValidationError("span digest mismatch")
        position = end
        # One first substantive sentence per span, at most. Extractive, not generated.
        match = re.search(r"[^.!?\n]{40,240}[.!?](?=\s|$)", piece)
        if match and len(proposals) < limit:
            excerpt = match.group().strip()
            offset = start + match.start() + len(match.group()) - len(match.group().lstrip())
            proposals.append({"segment_id": sid, "start": offset, "end": offset + len(excerpt),
                              "excerpt_sha256": hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
                              "review_status": "unverified_source_statement"})
    if position != len(transcript):
        raise CSFValidationError("incomplete source")
    return {"source_digest": digest, "segment_count": len(spans),
            "proposal_count": len(proposals), "proposals": proposals,
            "classification_performed": False, "external_writes": 0}
