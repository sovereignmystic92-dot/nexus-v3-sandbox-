"""Offline, evidence-bound claim candidates from verified transcript bytes.

No model inference, external calls, reviewer impersonation, or promotion.
"""
import hashlib
from dataclasses import dataclass

ALLOWED_KINDS = frozenset(("narrator_claim", "fictional_lore", "inference", "scientific_claim"))
MAX_CLAIMS = 100

@dataclass(frozen=True)
class ClaimExtraction:
    status: str
    candidates: tuple = ()
    reason: str = ""
    provider_writes: int = 0
    mastery_promoted: bool = False

def prepare_claim_candidates(source: bytes, *, expected_sha256: str,
                             source_id: str, claims):
    """Bind explicitly proposed claim interpretations to exact UTF-8 spans.

    Source bytes must match the externally verified archive digest. Each claim
    carries a quote that occurs exactly once. All results require independent
    review and are candidates only.
    """
    if type(source) is not bytes or type(expected_sha256) is not str:
        return ClaimExtraction("BLOCKED", reason="INVALID_SOURCE")
    if hashlib.sha256(source).hexdigest() != expected_sha256:
        return ClaimExtraction("BLOCKED", reason="SOURCE_DIGEST_MISMATCH")
    try:
        text = source.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return ClaimExtraction("BLOCKED", reason="INVALID_UTF8")
    if not isinstance(source_id, str) or not source_id.strip():
        return ClaimExtraction("BLOCKED", reason="MISSING_SOURCE_ID")
    if type(claims) not in (list, tuple) or not 1 <= len(claims) <= MAX_CLAIMS:
        return ClaimExtraction("BLOCKED", reason="INVALID_CLAIM_SET")
    result = []
    seen = set()
    for spec in claims:
        if type(spec) is not dict or set(spec) != {"claim_id", "quote", "interpretation", "kind"}:
            return ClaimExtraction("BLOCKED", reason="INVALID_CLAIM_SPEC")
        cid, quote, meaning, kind = (spec[k] for k in ("claim_id", "quote", "interpretation", "kind"))
        if any(type(x) is not str or not x.strip() for x in (cid, quote, meaning, kind)):
            return ClaimExtraction("BLOCKED", reason="EMPTY_CLAIM_FIELD")
        if cid in seen:
            return ClaimExtraction("BLOCKED", reason="DUPLICATE_CLAIM_ID")
        if kind not in ALLOWED_KINDS:
            return ClaimExtraction("BLOCKED", reason="UNKNOWN_CLAIM_KIND")
        if text.count(quote) != 1:
            return ClaimExtraction("BLOCKED", reason="EVIDENCE_NOT_UNIQUE")
        seen.add(cid)
        start = text.index(quote)
        byte_start = len(text[:start].encode("utf-8"))
        result.append({
            "claim_id": cid, "kind": kind, "interpretation": meaning,
            "source_id": source_id, "source_sha256": expected_sha256,
            "evidence_quote": quote, "byte_start": byte_start,
            "byte_end": byte_start + len(quote.encode("utf-8")),
            "review_status": "pending_independent_review",
            "truth_status": "unverified",
        })
    return ClaimExtraction("CANDIDATES_FOR_REVIEW", tuple(result))
