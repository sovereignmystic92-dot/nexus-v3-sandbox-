"""Bounded completion orchestration; callers provide authorized executors.

No service listener, credentials, provider writes, retry or automatic resume is
installed. Callbacks and checkpoint custody remain trusted host dependencies.
"""
from dataclasses import dataclass

STAGES = ('SOURCE_PRESERVED', 'CONTEXT_LOADED', 'DUPLICATES_CHECKED',
          'ANALYZED', 'PERSISTED', 'REGISTERED', 'READBACK_VERIFIED')


@dataclass(frozen=True)
class Receipt:
    run_id: str
    stage: str
    verified: bool
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class Result:
    status: str
    last_confirmed: str | None
    next_stage: str | None
    reason: str
    receipts: tuple[Receipt, ...]


def valid(receipt, run_id, stage):
    return (type(receipt) is Receipt and receipt.run_id == run_id
            and receipt.stage == stage and receipt.verified is True
            and type(receipt.evidence_refs) is tuple and bool(receipt.evidence_refs)
            and all(isinstance(ref, str) and ref for ref in receipt.evidence_refs))


def run(run_id, executors, save_checkpoint, read_checkpoint):
    """Run all authorized stages until a gate fails, with no user-prompt pauses.

    Each executor receives the immutable prior receipt tuple. Required stages
    cannot be omitted; a legitimately non-applicable action needs an explicit
    evidenced disposition from its executor. Exceptions stop without retry.
    Completion additionally requires independent checkpoint readback.

    This checks callback contracts, not the truth of arbitrary evidence refs.
    Host-specific executors must actually inspect source/output/routing state.
    A callback can bypass the library; chat-wide mandatory invocation is unproven.
    """
    if not isinstance(run_id, str) or not run_id:
        raise ValueError('Run identity required')
    if set(executors) != set(STAGES) or any(not callable(executors[s]) for s in STAGES):
        raise ValueError('Exactly the required stage executors must be supplied')
    confirmed = ()
    for stage in STAGES:
        try:
            receipt = executors[stage](confirmed)
        except Exception:
            return Result('BLOCKED', confirmed[-1].stage if confirmed else None,
                          stage, 'Stage outcome unavailable; reconcile before retry', confirmed)
        if not valid(receipt, run_id, stage):
            return Result('INCOMPLETE', confirmed[-1].stage if confirmed else None,
                          stage, 'Missing, unverified or misbound stage evidence', confirmed)
        candidate = confirmed + (receipt,)
        try:
            save_checkpoint(run_id, candidate)
            observed = read_checkpoint(run_id)
            matches = (type(observed) is tuple and len(observed) == len(candidate)
                       and all(valid(r, run_id, s) for r, s in zip(observed, STAGES))
                       and observed == candidate)
            if not matches:
                raise ValueError('Checkpoint mismatch')
        except Exception:
            return Result('BLOCKED', confirmed[-1].stage if confirmed else None,
                          stage, 'Stage may have executed; checkpoint unverified; reconcile only', confirmed)
        confirmed = candidate
    return Result('COMPLETE', confirmed[-1].stage, None,
                  'All required stage receipts and checkpoint readbacks verified', confirmed)
