"""Bind a verified WarFronts archive readback to Nexus SourceSnapshot.

Pure adapter only: no provider access, events, processing, writes or promotion.
"""
from dataclasses import dataclass

from .warfronts_source import WarFrontsSourcePlan
from .warfronts_archive_handoff import verify_archive_handoff
from .transcript_completion import SourceSnapshot, source_digest, validate_source


@dataclass(frozen=True)
class WarFrontsSnapshotBinding:
    source: SourceSnapshot
    archive_revision: str
    video_id: str
    status: str = "SOURCE_SNAPSHOT_READY_NOT_AUTHORIZED"
    provider_writes: int = 0


def bind_warfronts_snapshot(*, plan: WarFrontsSourcePlan, page_id: str,
                           parent_id: str, archive_video_id: str,
                           archive_channel_id: str, archive_text: str,
                           archive_source_url: str, archive_revision: str,
                           archive_complete: bool, independent_readback: bool):
    """Return a source snapshot only after the exact readback gate matches.

    Trusted host must prove Notion pagination, identity, revision and independent
    readback separately. A matching snapshot never authorizes a Cortex write.
    """
    verdict = verify_archive_handoff(
        plan=plan, archive_video_id=archive_video_id,
        archive_channel_id=archive_channel_id, archive_text=archive_text,
        archive_source_url=archive_source_url, archive_revision=archive_revision,
        archive_complete=archive_complete, independent_readback=independent_readback)
    if verdict.status != "READBACK_MATCHED_NOT_AUTHORIZED":
        raise ValueError("archive handoff not verified: " + verdict.next_action)
    if type(page_id) is not str or not page_id.strip():
        raise ValueError("missing canonical Notion page ID")
    if type(parent_id) is not str or not parent_id.strip() or parent_id == page_id:
        raise ValueError("invalid canonical Notion parent ID")
    source = SourceSnapshot(page_id, parent_id, plan.segments, True)
    validate_source(source)
    if source_digest(source) != plan.transcript_sha256:
        raise ValueError("source snapshot digest mismatch")
    return WarFrontsSnapshotBinding(source, archive_revision, plan.video_id)
