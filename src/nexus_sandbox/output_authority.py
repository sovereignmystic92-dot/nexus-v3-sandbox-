"""Nexus source/output destination contract (no provider calls or writes).

Notion owns verbatim source transcripts; Cortex owns developed Nexus outputs.
A validated route is NOT authorization to write or proof of persistence.
"""
import re
from dataclasses import dataclass

HEX64 = re.compile(r'^[0-9a-f]{64}$')
IDENT = re.compile(r'^[A-Za-z0-9:_./-]{1,256}$')
SOURCE_KIND = 'TRANSCRIPT'
OUTPUT_KIND = 'NEXUS_OUTPUT'


@dataclass(frozen=True)
class RouteVerdict:
    status: str
    next_action: str
    source_store: str
    output_store: str
    ready_to_write: bool = False
    completion_verified: bool = False


def validate_output_route(record, *, archive_readback_verified=False,
                          cortex_authority_verified=False,
                          cortex_output_readback_verified=False):
    """Validate source/output custody without inferring authority from contents.

    Mandatory source identity, revision and digest must be exact. Missing
    analytical details (research questions, connections) belong in a deferred
    queue and do not invalidate this routing decision.
    """
    def hold(action):
        return RouteVerdict('BLOCKED', action, 'NOTION', 'CORTEX')

    if type(record) is not dict or set(record) != {
            'source_kind', 'source_store', 'source_id', 'source_revision',
            'source_sha256', 'output_kind', 'output_store', 'output_id',
            'output_revision', 'output_source_id', 'output_source_sha256'}:
        return hold('FIX_ROUTE_SCHEMA')
    if any(type(v) is not str for v in record.values()):
        return hold('FIX_ROUTE_SCHEMA')
    for k in ('source_id', 'source_revision', 'output_id', 'output_revision'):
        if not IDENT.fullmatch(record[k]):
            return hold('FIX_ROUTE_IDENTITY')
    if (not HEX64.fullmatch(record['source_sha256']) or
            not HEX64.fullmatch(record['output_source_sha256'])):
        return hold('FIX_SOURCE_DIGEST')
    if record['source_kind'] != SOURCE_KIND or record['source_store'] != 'NOTION':
        return hold('ROUTE_TRANSCRIPT_TO_NOTION')
    if record['output_kind'] != OUTPUT_KIND or record['output_store'] != 'CORTEX':
        return hold('ROUTE_NEXUS_OUTPUT_TO_CORTEX')
    if (record['output_source_id'] != record['source_id'] or
            record['output_source_sha256'] != record['source_sha256']):
        return hold('RECONCILE_SOURCE_OUTPUT_LINK')
    if type(archive_readback_verified) is not bool or not archive_readback_verified:
        return hold('VERIFY_NOTION_SOURCE_READBACK')
    if type(cortex_authority_verified) is not bool or not cortex_authority_verified:
        return hold('VERIFY_CORTEX_WRITE_AUTHORITY')
    if type(cortex_output_readback_verified) is not bool:
        return hold('VERIFY_CORTEX_READBACK_PROOF')
    if not cortex_output_readback_verified:
        return RouteVerdict('ROUTED_NOT_COMPLETE',
                            'SAVE_AND_INDEPENDENTLY_READBACK_CORTEX_OUTPUT',
                            'NOTION', 'CORTEX')
    return RouteVerdict('ROUTE_VERIFIED', 'CHECK_REMAINING_PROCESSING_GATES',
                        'NOTION', 'CORTEX', False, True)


def legacy_notion_output_disposition(*, source_bound, cortex_equivalent_verified):
    """Never delete legacy Notion outputs or infer migrated state."""
    if type(source_bound) is not bool or type(cortex_equivalent_verified) is not bool:
        return 'HOLD_INVALID_EVIDENCE'
    if not source_bound:
        return 'DEFER_SOURCE_RECONCILIATION'
    if not cortex_equivalent_verified:
        return 'MIGRATION_REVIEW_REQUIRED'
    return 'PRESERVE_NOTION_LEGACY_AS_PROVENANCE'
