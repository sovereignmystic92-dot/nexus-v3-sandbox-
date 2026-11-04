"""Read-only, fail-closed bridge from host-verified Notion evidence to SQLite.

This module does not authenticate providers, write to Notion/Cortex, or run
automatically. Host assertions alone are not proof of external readback.
"""
from dataclasses import dataclass

from .transcript_ingestion import TranscriptCoordinator, digest_source


@dataclass(frozen=True)
class ArchiveBridgeResult:
    status: str
    next_action: str
    source_key: str | None = None
    provider_writes: int = 0
    automatic_execution: bool = False
    cp09: str = "NOT_PROVEN"


def record_verified_notion_archive(
    coordinator: TranscriptCoordinator, *, video_id: str, raw_transcript: str,
    source_page_id: str, observed_raw_transcript: str, observed_page_id: str,
    readback_ref: str, source_revision: str, observed_revision: str,
    host_readback_authenticated: bool = False,
) -> ArchiveBridgeResult:
    """Record a complete archive only after exact, source-bound host readback.

    The trusted host must independently authenticate the fetched page, full
    pagination, and revision. No network calls or provider writes occur here.
    """
    def hold(reason):
        return ArchiveBridgeResult("BLOCKED", reason)
    if type(host_readback_authenticated) is not bool or not host_readback_authenticated:
        return hold("AUTHENTICATE_FULL_NOTION_READBACK")
    if any(type(x) is not str or not x for x in
           (source_page_id, observed_page_id, readback_ref,
            source_revision, observed_revision)):
        return hold("REQUIRE_STABLE_SOURCE_AND_READBACK_IDENTIFIERS")
    if source_page_id != observed_page_id or source_revision != observed_revision:
        return hold("RECONCILE_NOTION_SOURCE_REVISION")
    try:
        expected_digest = digest_source(raw_transcript)
        observed_digest = digest_source(observed_raw_transcript)
    except (TypeError, ValueError, UnicodeError):
        return hold("REQUIRE_COMPLETE_RAW_TRANSCRIPT")
    if expected_digest != observed_digest or raw_transcript != observed_raw_transcript:
        return hold("RECONCILE_FULL_NOTION_TRANSCRIPT_BYTES")
    # The journal receives only a hash; no transcript text is written here.
    key = coordinator.receive(video_id, raw_transcript)
    evidence = {"destination": "notion:" + source_page_id,
                "readback": readback_ref,
                "source_revision": source_revision,
                "raw_sha256": expected_digest}
    coordinator.record(key, "NOTION_ARCHIVE_VERIFIED", "COMPLETE", evidence,
                       independently_read_back=True)
    return ArchiveBridgeResult("RECORDED", "VERIFY_PERSISTED_ANALYSIS", key)
