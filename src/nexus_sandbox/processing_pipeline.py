"""Bounded completion orchestration; callers provide authorized executors.

No service listener, credentials, provider writes, retry or automatic resume is
installed. Callbacks and checkpoint custody remain trusted host dependencies.
"""
from dataclasses import dataclass
import copy

STAGES = ('SOURCE_PRESERVED', 'CONTEXT_LOADED', 'DUPLICATES_CHECKED',
          'ANALYZED', 'PERSISTED', 'REGISTERED', 'READBACK_VERIFIED')


def run_resumable(binding, executors, save, read, reconcile):
    """Opt-in single-worker resume; externally provisioned checkpoint required.

    Store must durably save/read independent copies. Missing state holds, never
    initializes. Caller authenticates binding, evidence and current authority.
    Pending intent invokes observation-only reconciliation, never its executor.
    No host-loss storage or provider enforcement is installed by this function.
    """
    fields = {'run_id', 'source_id', 'source_sha256', 'destination_id',
              'policy_revision', 'code_revision', 'schema_version'}
    if (type(binding) is not dict or set(binding) != fields
            or binding['schema_version'] != 1
            or type(binding['schema_version']) is not int
            or any(type(binding[k]) is not str or not binding[k]
                   for k in fields - {'schema_version'})
            or len(binding['source_sha256']) != 64
            or any(c not in '0123456789abcdef' for c in binding['source_sha256'])):
        raise ValueError('Immutable complete processing binding required')
    if set(executors) != set(STAGES) or any(not callable(x) for x in executors.values()):
        raise ValueError('All seven executors required')
    binding = copy.deepcopy(binding)
    confirmed = ()
    stage = STAGES[0]
    def persist(state):
        save(binding['run_id'], copy.deepcopy(state))
        if read(binding['run_id']) != state:
            raise ValueError('Checkpoint readback mismatch')
    try:
        state = read(binding['run_id'])
        if (type(state) is not dict or set(state) != {'binding', 'receipts', 'pending'}
                or state['binding'] != binding or type(state['receipts']) is not tuple
                or len(state['receipts']) > len(STAGES)):
            raise ValueError('Missing or misbound checkpoint')
        saved = state['receipts']
        if not all(valid(r, binding['run_id'], s) for r, s in zip(saved, STAGES)):
            raise ValueError('Invalid ordered checkpoint receipts')
        confirmed = saved
        next_stage = STAGES[len(confirmed)] if len(confirmed) < len(STAGES) else None
        if state['pending'] is not None and state['pending'] != next_stage:
            raise ValueError('Misordered pending intent')
        if state['pending'] is not None:
            stage = state['pending']
            receipt = reconcile(stage, copy.deepcopy(binding), confirmed)
            if not valid(receipt, binding['run_id'], stage):
                raise ValueError('Uncertain action requires actual destination evidence')
            candidate = confirmed + (receipt,)
            state = {'binding': binding, 'receipts': candidate, 'pending': None}
            persist(state)
            confirmed = candidate
        for stage in STAGES[len(confirmed):]:
            state = {'binding': binding, 'receipts': confirmed, 'pending': stage}
            persist(state)  # Durable intent and readback before any effect.
            receipt = executors[stage](confirmed)
            if not valid(receipt, binding['run_id'], stage):
                raise ValueError('Stage outcome unverified')
            candidate = confirmed + (receipt,)
            persist({'binding': binding, 'receipts': candidate, 'pending': None})
            confirmed = candidate
    except Exception:
        return Result('BLOCKED', confirmed[-1].stage if confirmed else None,
                      stage, 'Checkpoint/outcome unverified; inspect saved intent and reconcile only',
                      confirmed)
    return Result('COMPLETE', STAGES[-1], None,
                  'Saved ordered receipts verified; no completed stage replayed', confirmed)


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

