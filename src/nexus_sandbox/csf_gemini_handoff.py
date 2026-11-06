"""Build a bounded, offline CSF Gemini handoff packet from a pinned checkout.

No network, credentials, Gemini calls, Notion/Cortex writes, or GitHub mutations.
The caller must independently verify checkout HEAD equals source_commit.
"""
import hashlib
import json
from pathlib import Path
import re

HANDOFF_ID = "handoff-2026-11-06-haiti-01"
ALLOWED_PATHS = (
    "docs/csf/haiti-review-candidates-v0.1.json",
    "schemas/csf_schema_v0.2.0.json",
    "src/nexus_sandbox/csf_v02.py",
    "src/nexus_sandbox/csf_transcript_ingest.py",
)
MAX_FILE_BYTES = 128_000
MAX_TOTAL_BYTES = 250_000


class HandoffError(ValueError):
    pass


def build_handoff(root, source_commit):
    """Return immutable source-bound manifest, not a claim of Gemini execution."""
    if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise HandoffError("exact 40-character source commit required")
    root = Path(root).resolve(strict=True)
    manifest = []
    total = 0
    for relative in ALLOWED_PATHS:
        path = root / relative
        if path.is_symlink() or not path.is_file() or path.resolve() != root.joinpath(relative):
            raise HandoffError("missing, symlinked or redirected handoff source")
        raw = path.read_bytes()
        if not raw or len(raw) > MAX_FILE_BYTES:
            raise HandoffError("missing or oversized handoff source")
        total += len(raw)
        if total > MAX_TOTAL_BYTES:
            raise HandoffError("handoff exceeds total byte budget")
        try:
            raw.decode("utf-8", errors="strict")
        except UnicodeError as error:
            raise HandoffError("source is not UTF-8") from error
        if relative.endswith(".json"):
            try:
                json.loads(raw)
            except ValueError as error:
                raise HandoffError("invalid JSON source") from error
        manifest.append({"path": relative, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
    return {
        "protocol_version": "csf-collab/0.1",
        "handoff_id": HANDOFF_ID,
        "source_commit": source_commit,
        "payload_ref": ALLOWED_PATHS[0],
        "sources": manifest,
        "status": "PREPARED_NOT_EXECUTED",
        "review_request": "Independent schema parity, provenance, identity collision and evidence-link audit; preserve disagreements.",
    }
