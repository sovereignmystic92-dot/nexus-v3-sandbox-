"""Offline, revision-bound identities for CSF v0.2.0 findings."""

import hashlib
import json

from .csf_notional_intake import prepare_source_receipt
from .csf_transcript_ingest import segment_transcript_bounded
from .csf_v02 import CSFValidationError, generate_finding_id, validate_finding

IDENTITY_VERSION = "1.0.0"


def _digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def bind_finding(source_envelope, finding, *, claim_id):
    """Wrap an offline finding using an assigned, replayed claim ID.

    The caller must supply the same assigned ID for revisions to the wording
    of a claim and distinct IDs for distinct claims in the same span. Findings
    must use default bounded segmentation and the full transcript digest.
    """
    if not isinstance(claim_id, str) or not claim_id or claim_id != claim_id.strip():
        raise CSFValidationError("assigned claim ID required")

    source = prepare_source_receipt(source_envelope)
    transcript = source_envelope["transcript"]
    bounded = segment_transcript_bounded(source["document_id"], transcript)
    spans = bounded["spans"]
    segments = {key: transcript[span["start"]:span["end"]]
                for key, span in spans.items()}
    validate_finding(finding, segments)
    reference = finding["source_reference"]
    if (reference["document_id"] != source["document_id"]
            or reference["content_digest"] != source["content_digest"]):
        raise CSFValidationError("finding source binding mismatch")

    span = spans[reference["segment_id"]]
    identity = {
        "identity_version": IDENTITY_VERSION,
        "document_id": source["document_id"],
        "source_revision": source["source_revision"],
        "source_sha256": source["content_digest"],
        "start": span["start"],
        "end": span["end"],
        "claim_id": claim_id,
    }
    key = _digest(identity)
    payload = {
        **identity,
        "finding_id": generate_finding_id(key),
        "idempotency_key": key,
        "source_url": source["source_url"],
        "segment_sha256": span["sha256"],
        "domain_id": finding["domain_id"],
        "claim_type": finding["claim_type"],
        "systemic_role": finding["systemic_role"],
        "assertion": finding["assertion"],
        "causal_links": [
            {**link, "evidence_refs": list(link["evidence_refs"])}
            for link in finding["causal_links"]
        ],
        "confidence_level": finding["confidence_level"],
        "confidence_rationale": finding["confidence_rationale"],
    }
    return {"payload": payload, "payload_sha256": _digest(payload)}
