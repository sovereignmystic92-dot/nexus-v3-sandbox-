"""Strict CP05 composition: Notion snapshot guard before Cortex checkpoint.

Only trusted host may attest authentication and complete inventory. This does
not make provider calls or provide a transactional Notion revision lock.
"""
from .notion_snapshot_guard import NotionSnapshot, compare_snapshots
from .cortex_checkpoint_bridge import (
    CortexCheckpointResult, record_verified_cortex_output,
)


def record_bound_cortex_output(coordinator, *, expected_notion: NotionSnapshot,
                               observed_notion: NotionSnapshot,
                               notion_host_authenticated: bool = False,
                               notion_inventory_complete: bool = False,
                               **cortex_kwargs) -> CortexCheckpointResult:
    verdict = compare_snapshots(
        expected_notion, observed_notion,
        authenticated=notion_host_authenticated,
        complete_inventory=notion_inventory_complete,
    )
    if verdict != "MATCHED":
        return CortexCheckpointResult("BLOCKED", verdict)
    source_key = cortex_kwargs.get("source_key")
    if not isinstance(source_key, str) or not source_key:
        return CortexCheckpointResult("BLOCKED", "REQUIRE_SOURCE_KEY")
    archive = coordinator.get(source_key, "NOTION_ARCHIVE_VERIFIED")
    if archive is None or archive.status != "COMPLETE" or not archive.verified:
        return CortexCheckpointResult("BLOCKED", "VERIFY_NOTION_ARCHIVE_CHECKPOINT")
    evidence = archive.evidence
    if (evidence.get("destination") != "notion:" + expected_notion.page_id
            or evidence.get("source_revision") != expected_notion.last_edited_at
            or evidence.get("page_content_sha256") != expected_notion.content_sha256):
        return CortexCheckpointResult("BLOCKED", "RECONCILE_NOTION_SNAPSHOT_CHECKPOINT")
    route = cortex_kwargs.get("route")
    if not isinstance(route, dict) or route.get("source_revision") != expected_notion.last_edited_at:
        return CortexCheckpointResult("BLOCKED", "RECONCILE_NOTION_ROUTE_REVISION")
    return record_verified_cortex_output(coordinator, **cortex_kwargs)
