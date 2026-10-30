"""Opt-in transcript checks for the existing pipeline; no live transport.

Trusted callers supply complete input, canonical IDs and fresh, fully paginated
snapshots. This cannot authenticate callbacks or force ordinary chat to use it.
"""
from dataclasses import dataclass
import hashlib

from .processing_pipeline import Receipt, run


@dataclass(frozen=True)
class SourceSnapshot:
    page_id: str
    parent_id: str
    segments: tuple[tuple[str, str], ...]
    complete: bool


@dataclass(frozen=True)
class OutputSnapshot:
    page_id: str
    parent_id: str
    source_id: str
    source_sha256: str
    archival_status: str
    complete: bool


@dataclass(frozen=True)
class TranscriptPlan:
    source: SourceSnapshot
    output_ids: tuple[str, ...]
    output_parent_id: str


def require(condition):
    if not condition:
        raise ValueError('Transcript evidence incomplete or inconsistent')


def source_digest(source):
    # No punctuation/whitespace normalization. Parsers must losslessly decode
    # provider markup before creating a snapshot; unsupported parsing must hold.
    return hashlib.sha256(''.join(text for _, text in source.segments).encode('utf-8')).hexdigest()


def validate_source(source):
    require(type(source) is SourceSnapshot and source.complete is True)
    require(type(source.page_id) is str and bool(source.page_id)
            and type(source.parent_id) is str and bool(source.parent_id))
    require(type(source.segments) is tuple and bool(source.segments))
    ids = []
    for segment in source.segments:
        require(type(segment) is tuple and len(segment) == 2)
        require(all(type(value) is str and bool(value) for value in segment))
        ids.append(segment[0])
    require(len(ids) == len(set(ids)))


def validate_plan(plan):
    require(type(plan) is TranscriptPlan)
    validate_source(plan.source)
    require(type(plan.output_ids) is tuple and bool(plan.output_ids)
            and all(type(x) is str and bool(x) for x in plan.output_ids)
            and len(set(plan.output_ids)) == len(plan.output_ids)
            and plan.source.page_id not in plan.output_ids)
    require(type(plan.output_parent_id) is str and bool(plan.output_parent_id))


def verify_source(plan, fetch_source):
    observed = fetch_source(plan.source.page_id)
    validate_source(observed)
    # Comparing segments checks interior text, order, IDs and boundaries too.
    require(observed == plan.source)
    return source_digest(observed)


def verify_completion(plan, fetch_source, fetch_output):
    """Read-only verification; never write, repair or retry on a failed read.

    Output status is structured source-archival status only, not historical
    accuracy or overall analytical completion. Prose contradictions require a
    separate reconciler; a caller must not present these checks as a prose audit.
    """
    validate_plan(plan)
    digest = verify_source(plan, fetch_source)
    for page_id in plan.output_ids:
        output = fetch_output(page_id)
        require(type(output) is OutputSnapshot and output.complete is True)
        require(output.page_id == page_id
                and output.parent_id == plan.output_parent_id
                and output.source_id == plan.source.page_id
                and output.source_sha256 == digest
                and output.archival_status == 'ARCHIVED')
    return digest


def run_transcript(run_id, plan, executors, save_checkpoint,
                   read_checkpoint, fetch_source, fetch_output):
    """Require source comparison before analysis and again before completion.

    Other stage executors still implement their existing semantic requirements.
    A blocked final check retains REGISTERED as the last confirmed checkpoint.
    Uses the non-resumable runner: this function does not authorize replay of
    effects after uncertainty; inspect checkpoints before a subsequent call.
    """
    validate_plan(plan)
    guarded = dict(executors)
    original_source = guarded['SOURCE_PRESERVED']
    original_final = guarded['READBACK_VERIFIED']

    def preserve(prior):
        receipt = original_source(prior)
        verify_source(plan, fetch_source)
        return receipt

    def complete(prior):
        receipt = original_final(prior)
        digest = verify_completion(plan, fetch_source, fetch_output)
        # Preserve the runner's validation of the original receipt as well.
        from .processing_pipeline import valid
        require(valid(receipt, run_id, 'READBACK_VERIFIED'))
        return Receipt(run_id, 'READBACK_VERIFIED', True,
                       receipt.evidence_refs + ('supplied-text-sha256:' + digest,))

    guarded['SOURCE_PRESERVED'] = preserve
    guarded['READBACK_VERIFIED'] = complete
    return run(run_id, guarded, save_checkpoint, read_checkpoint)
