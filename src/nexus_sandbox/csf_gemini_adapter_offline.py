"""Offline Gemini request builder and response parser for bounded CSF review.

No credentials, HTTP calls, transcript logs or persistence. Provider execution
requires a separately authorized host adapter and must not be inferred here.
"""
import json
from .csf_v02 import CSFValidationError
from .csf_independent_review_contract import validate_review_response

MAX_ITEMS = 12
MAX_REQUEST_BYTES = 48000
MAX_RESPONSE_BYTES = 48000


def build_gemini_review_request(packet):
    if not isinstance(packet, dict) or not isinstance(packet.get("review_items"), list):
        raise CSFValidationError("invalid review packet")
    items = packet["review_items"]
    if not 1 <= len(items) <= MAX_ITEMS or packet.get("review_item_count") != len(items):
        raise CSFValidationError("review batch exceeds bounds")
    if packet.get("provider_called") is not False or packet.get("external_writes") != 0:
        raise CSFValidationError("unsafe review packet state")
    # Context review only: model output is never independent fact corroboration.
    instruction = (
        "Review each quoted statement only against its supplied transcript context. "
        "A source assertion is not independently verified fact. Return exactly one "
        "review per item. Allowed verdicts: supported_by_context, "
        "contradicted_by_context, insufficient_context, ambiguous. "
        "Return a JSON object with source_digest and reviews. Each review must "
        "contain segment_id, start, end, excerpt_sha256, verdict and rationale. "
        "Never claim external verification or invent citations."
    )
    payload = {"source_digest": packet.get("source_digest"),
               "instructions": instruction,
               "items": [{k: item[k] for k in
                          ("segment_id", "start", "end", "excerpt_sha256", "excerpt",
                           "context", "context_start", "context_end")}
                         for item in items]}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    if len(encoded) > MAX_REQUEST_BYTES:
        raise CSFValidationError("review request too large")
    return {"request": payload, "request_bytes": len(encoded),
            "provider_called": False, "external_writes": 0}


def parse_gemini_review_response(packet, raw_response):
    if not isinstance(raw_response, str) or len(raw_response.encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise CSFValidationError("invalid response size")
    try:
        response = json.loads(raw_response)
    except (ValueError, TypeError) as exc:
        raise CSFValidationError("malformed reviewer JSON") from exc
    return validate_review_response(packet, response)
