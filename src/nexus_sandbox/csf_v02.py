"""Offline-only CSF v0.2.0 adapter. No Cortex/Notion writes or LLM calls."""
import hashlib
import json
import re
import uuid

VERSION = "0.2.0"
DOMAINS = frozenset(("gov_coordination", "inf_supply", "geo_dependencies"))
KINDS = frozenset(("observation", "inference", "scenario"))
ROLES = frozenset(("structural_bottleneck", "feedback_loop", "institutional_failure", "resilience_factor"))
DIRECTIONS = frozenset(("accelerates", "mitigates", "triggers", "constrains"))
STATUSES = frozenset(("hypothesized", "supported", "disputed", "rejected"))
CONFIDENCES = frozenset(("low", "medium", "high", "unassessed"))
FIELDS = frozenset(("contract_version", "finding_id", "idempotency_key", "source_reference",
                    "domain_id", "claim_type", "systemic_role", "assertion", "causal_links",
                    "confidence_level", "confidence_rationale"))
SOURCE_FIELDS = frozenset(("document_id", "content_digest", "transcript_segment",
                           "segment_id", "timestamp_or_line"))
LINK_FIELDS = frozenset(("target_domain", "direction", "mechanism", "evidence_refs",
                         "verification_status"))


class CSFValidationError(ValueError):
    pass


def normalize_assertion(assertion):
    if not isinstance(assertion, str) or not assertion.strip():
        raise CSFValidationError("assertion required")
    return assertion.strip().lower()


def generate_idempotency_key(document_id, content_digest, assertion):
    if not isinstance(document_id, str) or not document_id.strip():
        raise CSFValidationError("document_id required")
    if not isinstance(content_digest, str) or not re.fullmatch(r"[a-f0-9]{64}", content_digest):
        raise CSFValidationError("invalid content digest")
    raw = f"{document_id}:{content_digest}:{normalize_assertion(assertion)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_finding_id(idempotency_key):
    if not isinstance(idempotency_key, str) or not re.fullmatch(r"[a-f0-9]{64}", idempotency_key):
        raise CSFValidationError("invalid idempotency key")
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, idempotency_key))


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate_finding(record, known_segments=None):
    """Validate schema shape and semantic references; known_segments must be from verified source."""
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise CSFValidationError("missing or unknown finding fields")
    if record["contract_version"] != VERSION:
        raise CSFValidationError("unsupported contract version")
    src = record["source_reference"]
    if not isinstance(src, dict) or not {"document_id", "content_digest", "transcript_segment", "segment_id"} <= set(src) or not set(src) <= SOURCE_FIELDS:
        raise CSFValidationError("invalid source shape")
    if not all(_nonempty(src[k]) for k in ("document_id", "transcript_segment", "segment_id")):
        raise CSFValidationError("empty source reference")
    if "timestamp_or_line" in src and not _nonempty(src["timestamp_or_line"]):
        raise CSFValidationError("invalid source location")
    if not isinstance(src["content_digest"], str) or not re.fullmatch(r"[a-f0-9]{64}", src["content_digest"]):
        raise CSFValidationError("invalid content digest")
    if record["domain_id"] not in DOMAINS or record["claim_type"] not in KINDS or record["systemic_role"] not in ROLES:
        raise CSFValidationError("invalid classification")
    if not _nonempty(record["assertion"]) or len(record["assertion"]) > 300:
        raise CSFValidationError("invalid assertion")
    if record["confidence_level"] not in CONFIDENCES or not _nonempty(record["confidence_rationale"]):
        raise CSFValidationError("invalid confidence")
    expected = generate_idempotency_key(src["document_id"], src["content_digest"], record["assertion"])
    if record["idempotency_key"] != expected or record["finding_id"] != generate_finding_id(expected):
        raise CSFValidationError("identity mismatch")
    if known_segments is not None:
        if src["segment_id"] not in known_segments or known_segments[src["segment_id"]] != src["transcript_segment"]:
            raise CSFValidationError("source segment not verified")
    links = record["causal_links"]
    if not isinstance(links, list):
        raise CSFValidationError("invalid causal links")
    for link in links:
        if not isinstance(link, dict) or set(link) != LINK_FIELDS:
            raise CSFValidationError("invalid causal link shape")
        refs = link["evidence_refs"]
        if (link["target_domain"] not in DOMAINS or link["direction"] not in DIRECTIONS
            or link["verification_status"] not in STATUSES or not _nonempty(link["mechanism"])
            or not isinstance(refs, list) or not refs or any(not _nonempty(x) for x in refs)
            or len(refs) != len(set(refs))):
            raise CSFValidationError("invalid causal link")
        if known_segments is not None and any(ref not in known_segments for ref in refs):
            raise CSFValidationError("orphan evidence reference")
    return True


def make_finding(document_id, segment_id, transcript_segment, assertion, domain_id,
                 claim_type, systemic_role, *, content_digest=None, causal_links=None,
                 confidence_level="unassessed", confidence_rationale="Independent review pending"):
    """Explicit classification input; does not hallucinate extracted claims."""
    if content_digest is None:
        content_digest = hashlib.sha256(transcript_segment.encode("utf-8")).hexdigest()
    key = generate_idempotency_key(document_id, content_digest, assertion)
    finding = {
        "contract_version": VERSION, "finding_id": generate_finding_id(key),
        "idempotency_key": key,
        "source_reference": {"document_id": document_id, "content_digest": content_digest,
                             "transcript_segment": transcript_segment, "segment_id": segment_id},
        "domain_id": domain_id, "claim_type": claim_type, "systemic_role": systemic_role,
        "assertion": assertion, "causal_links": causal_links or [],
        "confidence_level": confidence_level, "confidence_rationale": confidence_rationale,
    }
    validate_finding(finding, {segment_id: transcript_segment} if not causal_links else None)
    return finding


def deduplicate(findings):
    """Pure in-memory idempotent upsert, preserving first-seen records."""
    by_key = {}
    for finding in findings:
        validate_finding(finding)
        key = finding["idempotency_key"]
        if key in by_key and by_key[key] != finding:
            raise CSFValidationError("conflicting records share idempotency key")
        by_key[key] = finding
    return list(by_key.values())
