"""Compose an exact, already archived source with the bounded Cortex handoff.

The host supplies authenticated ports and current destination-specific grants.
This opt-in path has no Notion writer, credentials, trigger or retry loop.
"""
import json
from uuid import UUID

from .transcript_ingestion_gate import plan_archive_resume
from .transcript_live_handoff import Handoff, Observed, run_handoff


def run_archived_handoff(*, prepared, notion_page_id, expected_source_sha256,
                         read_archive, cortex_module_name, analysis,
                         cortex_read, cortex_write, allow_cortex_write=False):
    """read_archive has the existing NotionArchivePort.read_archive signature.

    Every observation must be complete, bound and byte-exact. An existing
    archive is required; missing chunks cannot trigger source writes. Recheck
    source before an output write and after output readback. Source races still
    require provider fencing: these observations are not an atomic transaction.
    A blocked/uncertain result must be reconciled before any later invocation.
    """
    if str(UUID(notion_page_id)) != notion_page_id:
        raise ValueError('canonical Notion archive UUID required')
    if type(allow_cortex_write) is not bool:
        raise ValueError('explicit boolean Cortex authorization required')
    # Own the pinned input; callbacks cannot change the expected payload.
    pinned = json.loads(json.dumps(prepared))
    plan_archive_resume(pinned, notion_page_id, None,
                        expected_source_sha256=expected_source_sha256)
    transcript = ''.join(pinned['chunks'])

    def source_read(key):
        if key != notion_page_id:
            raise ValueError('archive destination changed')
        observation = read_archive(key, expected_source_sha256)
        decision = plan_archive_resume(pinned, key, observation,
                                       expected_source_sha256=expected_source_sha256)
        if decision['state'] != 'ARCHIVE_VERIFIED':
            raise ValueError('complete exact archive readback required')
        return Observed(key, ''.join(c['text'] for c in observation['chunks']))

    def no_source_write(*args):
        raise PermissionError('archived handoff cannot write the source')

    def output_write(key, text):
        source_read(notion_page_id)
        cortex_write(key, text)

    result = run_handoff(
        transcript=transcript, notion_page_id=notion_page_id,
        cortex_module_name=cortex_module_name, analysis=analysis,
        notion_read=source_read, notion_write=no_source_write,
        cortex_read=cortex_read, cortex_write=output_write,
        allow_notion_write=False, allow_cortex_write=allow_cortex_write)
    if result.status == 'READBACK_MATCHED':
        try:
            source_read(notion_page_id)
        except Exception:
            return Handoff('BLOCKED', 'RECONCILE_ARCHIVE_AFTER_CORTEX_READBACK',
                           expected_source_sha256, notion_page_id, cortex_module_name)
    return result
