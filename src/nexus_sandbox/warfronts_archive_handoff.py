"""Offline WarFronts-to-Notion readback binding; no provider I/O or writes."""
from dataclasses import dataclass
import hashlib

from .warfronts_source import WarFrontsSourcePlan


@dataclass(frozen=True)
class ArchiveHandoff:
    status: str
    next_action: str
    video_id: str
    source_sha256: str
    provider_writes: int = 0


def verify_archive_handoff(*, plan: WarFrontsSourcePlan, archive_video_id: str,
                           archive_channel_id: str, archive_text: str,
                           archive_source_url: str, archive_revision: str,
                           archive_complete: bool, independent_readback: bool):
    """Require exact canonical text and identity on a host-supplied readback.

    The host must independently obtain and authenticate the Notion readback;
    flags and strings alone cannot establish provider authenticity.
    """
    if type(plan) is not WarFrontsSourcePlan:
        raise ValueError("invalid source plan")
    def hold(reason):
        return ArchiveHandoff("BLOCKED", reason, plan.video_id, plan.transcript_sha256)
    if type(archive_complete) is not bool or type(independent_readback) is not bool:
        return hold("INVALID_READBACK_ASSERTIONS")
    if not archive_complete or not independent_readback:
        return hold("AWAIT_INDEPENDENT_NOTION_READBACK")
    if type(archive_revision) is not str or not archive_revision.strip():
        return hold("MISSING_NOTION_REVISION")
    if (type(archive_video_id) is not str or archive_video_id != plan.video_id or
            type(archive_channel_id) is not str or archive_channel_id != plan.channel_id or
            type(archive_source_url) is not str or archive_source_url != plan.source_url):
        return hold("RECONCILE_SOURCE_IDENTITY")
    if type(archive_text) is not str:
        return hold("RECONCILE_ARCHIVE_TEXT")
    expected_text = "".join(text for _, text in plan.segments)
    digest = hashlib.sha256(archive_text.encode("utf-8")).hexdigest()
    if archive_text != expected_text or digest != plan.transcript_sha256:
        return hold("RECONCILE_ARCHIVE_TEXT")
    return ArchiveHandoff("READBACK_MATCHED_NOT_AUTHORIZED", "AUTHENTICATE_EVENT_AND_CORTEX_ROUTE",
                          plan.video_id, digest)
