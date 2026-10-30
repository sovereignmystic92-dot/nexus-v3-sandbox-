"""Read-only composition gate for source-bound transcript inspection.

A checked route may plan an inspection, not execute work, write Cortex or
count completion. The trusted host authenticates source/event/provider evidence.
"""
from dataclasses import dataclass

from .event_router import Event, Enrollment, ObserverQueue
from .output_authority import validate_output_route
from .transcript_completion import SourceSnapshot, validate_source, source_digest


@dataclass(frozen=True)
class TranscriptIntakeDecision:
    status: str
    next_action: str
    job_id: str | None = None
    provider_writes: int = 0
    automatic_execution: bool = False
    cp09: str = 'NOT_PROVEN'


def prepare_transcript_inspection(
        *, source: SourceSnapshot, route_record: dict, event: Event,
        enrollment: Enrollment, queue: ObserverQueue,
        archive_readback_verified: bool, event_authenticated: bool,
        source_revision_verified: bool, cortex_authority_verified: bool):
    """Plan only after trusted Notion->Cortex mapping and exact source digest.

    The caller must independently verify that source is the full, paginated,
    canonical Notion record; that event origin is authenticated; that the source
    revision matches the authoritative Notion version; and that Cortex authority
    is current. These are strictly Boolean host assertions, not evidence by
    themselves. This function does not advance any completion/promotion state.
    """
    def hold(action):
        return TranscriptIntakeDecision('BLOCKED', action)

    if any(type(flag) is not bool for flag in (
            archive_readback_verified, event_authenticated,
            source_revision_verified, cortex_authority_verified)):
        return hold('VERIFY_TRUSTED_HOST_ASSERTIONS')
    if not archive_readback_verified:
        return hold('VERIFY_NOTION_SOURCE_READBACK')
    if not event_authenticated:
        return hold('AUTHENTICATE_SOURCE_EVENT')
    if not source_revision_verified:
        return hold('VERIFY_NOTION_SOURCE_REVISION')
    if not cortex_authority_verified:
        return hold('VERIFY_CORTEX_DESTINATION_AUTHORITY')
    try:
        validate_source(source)
        digest = source_digest(source)
    except (ValueError, TypeError, UnicodeError):
        return hold('RECONCILE_TRANSCRIPT_SOURCE')
    if type(route_record) is not dict:
        return hold('FIX_ROUTE_SCHEMA')
    if (source.page_id != route_record.get('source_id') or
            digest != route_record.get('source_sha256')):
        return hold('RECONCILE_NOTION_SOURCE_BINDING')
    if (type(event) is not Event or event.kind not in
            ('SOURCE_READY', 'SOURCE_REVISION_CHANGED') or
            event.origin != 'SOURCE' or
            event.source_id != source.page_id or
            event.revision_sha256 != digest):
        return hold('REJECT_OR_RECONCILE_EVENT')
    verdict = validate_output_route(
        route_record, archive_readback_verified=True,
        cortex_authority_verified=True,
        cortex_output_readback_verified=False)
    # Before an output is written, a correct destination is expected to be
    # ROUTED_NOT_COMPLETE. No output readback or completion is inferred.
    if verdict.status != 'ROUTED_NOT_COMPLETE':
        return hold(verdict.next_action)
    try:
        decision = queue.route(event, enrollment)
    except (ValueError, TypeError):
        return hold('RECONCILE_ENROLLED_EVENT')
    if decision.status == 'PLANNED':
        return TranscriptIntakeDecision('PLANNED',
                  'INSPECT_NOTION_TRANSCRIPT_FOR_CORTEX_OUTPUT',decision.job_id)
    if decision.status == 'DUPLICATE':
        return TranscriptIntakeDecision('DUPLICATE','NO_REPLAY',decision.job_id)
    return hold('REVIEW_ENROLLMENT_OR_EVENT')
