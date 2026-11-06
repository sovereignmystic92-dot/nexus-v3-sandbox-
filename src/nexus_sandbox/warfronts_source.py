"""WarFronts pilot: offline, lossless caption intake planning.

This module never fetches YouTube, invokes Gemini, or writes Notion/Cortex.
A trusted host must obtain captions, prove their provenance/completeness,
archive and independently read back Notion, and authenticate the source event.
"""
from dataclasses import dataclass
import hashlib
import re

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


@dataclass(frozen=True)
class CaptionSegment:
    sequence: int
    start_ms: int
    duration_ms: int
    text: str


@dataclass(frozen=True)
class WarFrontsSourcePlan:
    video_id: str
    source_url: str
    transcript_sha256: str
    segments: tuple[tuple[str, str], ...]
    status: str = "AWAITING_NOTION_ARCHIVE_READBACK"


def prepare_warfronts_source(*, video_id, segments, channel_verified,
                             captions_complete, caption_provenance_verified):
    """Validate a supplied caption sequence; never claim provider verification.

    Boolean evidence flags must be asserted by a trusted host, not Gemini.
    Digest preserves exact caption text, without whitespace normalization.
    Segment identity/order and timing are retained separately for archiving.
    """
    if type(video_id) is not str or not VIDEO_ID.fullmatch(video_id):
        raise ValueError("invalid YouTube video ID")
    if any(type(flag) is not bool or not flag for flag in (
            channel_verified, captions_complete, caption_provenance_verified)):
        raise ValueError("unverified channel or incomplete/unproven captions")
    if type(segments) is not tuple or not segments:
        raise ValueError("missing captions")
    previous_start = -1
    prepared = []
    for index, item in enumerate(segments):
        if type(item) is not CaptionSegment or type(item.sequence) is not int or item.sequence != index:
            raise ValueError("noncanonical caption order")
        if (type(item.start_ms) is not int or type(item.duration_ms) is not int
                or item.start_ms < 0 or item.duration_ms <= 0
                or item.start_ms < previous_start):
            raise ValueError("invalid caption timing")
        if type(item.text) is not str or not item.text:
            raise ValueError("missing caption text")
        previous_start = item.start_ms
        prepared.append((f"{item.sequence}:{item.start_ms}:{item.duration_ms}", item.text))
    transcript = "".join(text for _, text in prepared)
    return WarFrontsSourcePlan(
        video_id, "https://www.youtube.com/watch?v=" + video_id,
        hashlib.sha256(transcript.encode("utf-8")).hexdigest(), tuple(prepared))
