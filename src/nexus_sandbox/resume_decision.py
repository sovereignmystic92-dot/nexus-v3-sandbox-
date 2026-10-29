"""Read-only decision for a previously enrolled Nexus processing checkpoint.

This module cannot execute actions or mutate checkpoint storage. The caller must
supply a complete, independently observed checkpoint and fresh authority evidence.
It augments, rather than replaces, processing_pipeline.run_resumable.
"""
from dataclasses import dataclass
from .checkpoint_json import decode
from .processing_pipeline import STAGES


@dataclass(frozen=True)
class ResumeDecision:
    status: str
    completed: tuple[str, ...]
    pending: str | None
    next_action: str
    reason: str


def decide_resume(checkpoint_text, binding, *, inventory_complete: bool,
                  authority_verified: bool) -> ResumeDecision:
    """Classify a checkpoint, never authorize or perform the underlying action.

    No missing-state initialization, no replay after an unacknowledged action,
    and no inference from a partial inventory or stale credentials.
    """
    if type(inventory_complete) is not bool or type(authority_verified) is not bool:
        raise ValueError('Boolean evidence flags required')
    if not inventory_complete:
        return ResumeDecision('BLOCKED', (), None, 'OBTAIN_COMPLETE_INVENTORY',
                              'Checkpoint observation may be incomplete')
    if not authority_verified:
        return ResumeDecision('BLOCKED', (), None, 'VERIFY_CURRENT_AUTHORITY',
                              'Current permission, identity or lease is unverified')
    try:
        state = decode(checkpoint_text, binding)
    except (ValueError, TypeError, KeyError, AttributeError):
        return ResumeDecision('BLOCKED', (), None, 'INVESTIGATE_CHECKPOINT',
                              'Checkpoint is missing, malformed, or misbound')
    completed = tuple(r.stage for r in state['receipts'])
    pending = state['pending']
    if pending is not None:
        return ResumeDecision('RECONCILE_ONLY', completed, pending,
                              'OBSERVE_DESTINATION_AND_RECONCILE',
                              'Durable intent exists; result is not confirmed. Never replay blindly')
    if len(completed) == len(STAGES):
        return ResumeDecision('COMPLETE', completed, None, 'NO_ACTION',
                              'All ordered receipts are present in the verified checkpoint')
    return ResumeDecision('READY_FOR_GATED_EXECUTOR', completed, STAGES[len(completed)],
                          'VERIFY_PREREQUISITES_AND_SAVE_INTENT',
                          'No pending intent; executable work still requires an authorized executor')
