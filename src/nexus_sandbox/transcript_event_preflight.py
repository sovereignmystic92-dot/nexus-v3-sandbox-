"""Strict source-bound event preflight. No provider calls or authorization grants."""
import hashlib
import re

HEX = re.compile(r"[0-9a-f]{64}\Z")
FIELDS = {"schema", "event_id", "source_ref", "source_sha256",
          "source_byte_count", "idempotency_key", "event_kind"}
SCHEMA = "NEXUS_TRANSCRIPT_EVENT_V2"

def validate_event(event, *, raw_source, expected_source_ref, authorized_event_id):
    if not isinstance(event, dict) or set(event) != FIELDS:
        raise ValueError("event schema fields mismatch")
    if event["schema"] != SCHEMA or event["event_kind"] != "SOURCE_READY":
        raise ValueError("unsupported event")
    for key in ("event_id", "source_ref", "idempotency_key"):
        value = event[key]
        if type(value) is not str or not value or len(value) > 512:
            raise ValueError("invalid " + key)
    if event["event_id"] != authorized_event_id:
        raise ValueError("unapproved event ID")
    if event["source_ref"] != expected_source_ref:
        raise ValueError("source binding mismatch")
    if type(raw_source) is not bytes or not raw_source:
        raise ValueError("immutable raw source bytes required")
    if type(event["source_byte_count"]) is not int or event["source_byte_count"] != len(raw_source):
        raise ValueError("source length mismatch")
    digest = hashlib.sha256(raw_source).hexdigest()
    if type(event["source_sha256"]) is not str or not HEX.fullmatch(event["source_sha256"]):
        raise ValueError("invalid source checksum")
    if digest != event["source_sha256"]:
        raise ValueError("source checksum mismatch")
    expected_key = hashlib.sha256((event["source_ref"] + "\n" + digest).encode("utf-8")).hexdigest()
    if event["idempotency_key"] != expected_key:
        raise ValueError("idempotency key mismatch")
    return {"source_sha256": digest, "source_byte_count": len(raw_source),
            "idempotency_key": expected_key, "event_id": event["event_id"]}
