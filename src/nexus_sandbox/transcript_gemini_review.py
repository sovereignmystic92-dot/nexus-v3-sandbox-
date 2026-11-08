"""Bind independent Gemini review evidence to an exact Nexus transcript source.

No Gemini API calls or provider writes. Host must authenticate the reviewer
and supply its response; this code rejects stale or cross-source responses.
"""
import hashlib
from dataclasses import dataclass

@dataclass(frozen=True)
class GeminiReview:
    source_sha256: str
    source_ref: str
    model: str
    review_text: str
    review_sha256: str
    invocation_id: str


def validate_gemini_review(review, *, source_sha256, source_ref):
    if type(review) is not GeminiReview:
        raise ValueError("structured Gemini review required")
    if type(source_sha256) is not str or len(source_sha256) != 64:
        raise ValueError("invalid source digest")
    if review.source_sha256 != source_sha256 or review.source_ref != source_ref:
        raise ValueError("Gemini review source binding mismatch")
    for value in (review.model, review.review_text, review.invocation_id):
        if type(value) is not str or not value.strip():
            raise ValueError("incomplete Gemini review evidence")
    if type(review.review_sha256) is not str or hashlib.sha256(
        review.review_text.encode("utf-8")).hexdigest() != review.review_sha256:
        raise ValueError("Gemini review digest mismatch")
    return {"source_sha256": source_sha256,
            "review_sha256": review.review_sha256,
            "invocation_id": review.invocation_id,
            "model": review.model}
