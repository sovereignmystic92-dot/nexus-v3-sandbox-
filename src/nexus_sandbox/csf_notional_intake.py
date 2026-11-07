"""Read-only bridge from a fetched canonical transcript to a CSF intake receipt.

No provider calls, writes, or invented candidate claims. Input is an explicitly
exported source envelope from an authorized host. This is not a Notion client.
"""
import hashlib
import json
from pathlib import Path

from .csf_transcript_ingest import segment_transcript
from .csf_v02 import CSFValidationError

REQUIRED = {"source_url", "source_revision", "document_id", "transcript", "expected_sha256"}


def prepare_source_receipt(envelope):
    if not isinstance(envelope, dict) or set(envelope) != REQUIRED:
        raise CSFValidationError("exact source envelope fields required")
    url = envelope["source_url"]
    revision = envelope["source_revision"]
    digest = envelope["expected_sha256"]
    if not isinstance(url, str) or not url.startswith("https://app.notion.com/p/"):
        raise CSFValidationError("canonical Notion source URL required")
    if not isinstance(revision, str) or not revision.strip():
        raise CSFValidationError("source revision required")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise CSFValidationError("expected SHA-256 required")
    transcript = envelope["transcript"]
    if not isinstance(transcript, str):
        raise CSFValidationError("transcript must be text")
    actual = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
    if actual != digest:
        raise CSFValidationError("source digest mismatch")
    source = segment_transcript(envelope["document_id"], transcript)
    if source["content_digest"] != digest:
        raise CSFValidationError("segmentation digest mismatch")
    return {
        "status": "READ_ONLY_SOURCE_PREPARED",
        "source_url": url,
        "source_revision": revision,
        "document_id": source["document_id"],
        "content_digest": digest,
        "segment_count": len(source["segments"]),
        "segments": source["segments"],
        "candidates": [],
        "provider_called": False,
        "external_writes": 0,
        "audit_gate_promoted": False,
    }
