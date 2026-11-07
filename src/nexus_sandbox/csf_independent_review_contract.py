"""Strict, provider-neutral contract for independent review of source statements.

A model's assessment is not independent external corroboration. No provider calls,
network, persistence or automatic gate promotion occur in this module.
"""
import hashlib
from .csf_v02 import CSFValidationError

VERDICTS = frozenset({"supported_by_context", "contradicted_by_context",
                      "insufficient_context", "ambiguous"})


def validate_review_response(packet, response):
    if not isinstance(packet, dict) or not isinstance(response, dict):
        raise CSFValidationError("invalid review envelope")
    if set(response) != {"source_digest", "reviews"}:
        raise CSFValidationError("unexpected review response fields")
    if response["source_digest"] != packet.get("source_digest"):
        raise CSFValidationError("review source mismatch")
    items = packet.get("review_items")
    reviews = response["reviews"]
    if not isinstance(items, list) or not isinstance(reviews, list) or len(items) != len(reviews):
        raise CSFValidationError("incomplete review")
    if packet.get("provider_called") is not False or packet.get("external_writes") != 0:
        raise CSFValidationError("invalid source packet state")
    expected = {}
    for item in items:
        if not isinstance(item, dict):
            raise CSFValidationError("invalid source item")
        key = (item.get("segment_id"), item.get("start"), item.get("end"))
        if key in expected:
            raise CSFValidationError("duplicate source reference")
        excerpt = item.get("excerpt")
        if not isinstance(excerpt, str) or hashlib.sha256(excerpt.encode("utf-8")).hexdigest() != item.get("excerpt_sha256"):
            raise CSFValidationError("invalid excerpt fingerprint")
        expected[key] = item["excerpt_sha256"]
    seen = set()
    normalized = []
    for review in reviews:
        if not isinstance(review, dict) or set(review) != {"segment_id", "start", "end", "excerpt_sha256", "verdict", "rationale"}:
            raise CSFValidationError("invalid review fields")
        key = (review["segment_id"], review["start"], review["end"])
        if key not in expected or key in seen or review["excerpt_sha256"] != expected[key]:
            raise CSFValidationError("review reference mismatch")
        if review["verdict"] not in VERDICTS or not isinstance(review["rationale"], str) or not 1 <= len(review["rationale"].strip()) <= 1000:
            raise CSFValidationError("invalid review verdict")
        seen.add(key)
        normalized.append(dict(review))
    if seen != set(expected):
        raise CSFValidationError("missing reviews")
    return {"source_digest": response["source_digest"], "review_count": len(normalized),
            "reviews": normalized, "review_scope": "transcript_context_only",
            "external_corroboration": False, "factual_verification": False,
            "approved_for_persistence": False, "audit_gate_promoted": False}
