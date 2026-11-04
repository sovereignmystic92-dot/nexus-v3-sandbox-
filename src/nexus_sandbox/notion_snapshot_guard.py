"""Fail-closed comparison of independently obtained Notion page snapshots.

This is pure validation, not proof of provider authentication, revision locking,
complete pagination, or the Nexus runtime's executing identity.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

_SHA = re.compile(r"^[0-9a-f]{64}$")
_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z$")


@dataclass(frozen=True)
class NotionSnapshot:
    page_id: str
    last_edited_at: str
    content_sha256: str


def snapshot(page_id: str, last_edited_at: str, complete_text: str) -> NotionSnapshot:
    """Digest canonical full text supplied by a trusted host, never an excerpt."""
    if not isinstance(page_id, str) or not page_id.strip():
        raise ValueError("Missing page identity")
    if not isinstance(last_edited_at, str) or not _TIME.fullmatch(last_edited_at):
        raise ValueError("Missing provider last-edited timestamp")
    if not isinstance(complete_text, str) or not complete_text.strip():
        raise ValueError("Missing complete page text")
    return NotionSnapshot(page_id, last_edited_at,
                          hashlib.sha256(complete_text.encode("utf-8")).hexdigest())


def compare_snapshots(expected: NotionSnapshot, observed: NotionSnapshot,
                      *, authenticated: bool = False,
                      complete_inventory: bool = False) -> str:
    """Return MATCHED only with explicit host attestations and exact equality.

    A timestamp is a change detector, not a transactional revision lock.
    """
    if type(authenticated) is not bool or type(complete_inventory) is not bool:
        return "BLOCKED_UNTRUSTED_HOST_FLAGS"
    if not authenticated or not complete_inventory:
        return "BLOCKED_UNVERIFIED_HOST_OR_INCOMPLETE_PAGE"
    if not isinstance(expected, NotionSnapshot) or not isinstance(observed, NotionSnapshot):
        return "BLOCKED_INVALID_SNAPSHOT"
    for item in (expected, observed):
        if not item.page_id.strip() or not _TIME.fullmatch(item.last_edited_at) or not _SHA.fullmatch(item.content_sha256):
            return "BLOCKED_INVALID_SNAPSHOT"
    if expected.page_id != observed.page_id:
        return "BLOCKED_PAGE_MISMATCH"
    if expected.last_edited_at != observed.last_edited_at:
        return "BLOCKED_CHANGED_TIMESTAMP"
    if expected.content_sha256 != observed.content_sha256:
        return "BLOCKED_CHANGED_CONTENT"
    return "MATCHED"
