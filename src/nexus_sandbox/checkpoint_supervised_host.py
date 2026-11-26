"""Opt-in owner-invoked checkpoint custody; trusted callbacks supply authority.

No scheduled mode, provider adapter, update path, journal reconstruction or CAS.
"""
import copy
import fcntl
import hashlib
import json
from pathlib import Path

from .supervised_journal_custody import expected_binding, _inspect, _snapshot
from .transcript_supervised_host import execute_supervised


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                    separators=(',', ':')).encode()).hexdigest()


def execute_checkpoint_supervised(*, context, supervised_kwargs, initialize=False,
                                 read_checkpoint, write_checkpoint, verify_assignment):
    """Checkpoint ports read/write the exact transaction's private envelope.

    read returns None only for confirmed absence. write has no retry semantics.
    verify_assignment freshly returns the exact owner-invoked assignment below,
    from authoritative host evidence, or raises. Caller flags are not authority.
    """
    ctx = copy.deepcopy(context)
    fields = {'transaction_id', 'assignment_id', 'actor', 'source_revision',
              'code_revision', 'policy_revision', 'destination'}
    if (type(ctx) is not dict or set(ctx) != fields or type(initialize) is not bool
            or any(type(ctx[k]) is not str or not ctx[k].strip() or len(ctx[k]) > 512
                   for k in fields - {'destination'})
            or type(ctx['destination']) is not dict
            or set(ctx['destination']) != {'parent', 'dependencies'}
            or ctx['destination']['parent'] is not None
                and type(ctx['destination']['parent']) is not str
            or type(ctx['destination']['dependencies']) is not list
            or any(type(x) is not str for x in ctx['destination']['dependencies'])):
        raise ValueError('Exact supervised context required')
    args = dict(supervised_kwargs)
    if set(args) != {'journal_path', 'prepared', 'source_page', 'source_sha256',
                     'output_name', 'analysis', 'expected_owner', 'request',
                     'allow_create', 'analysis_gate'}:
        raise ValueError('Create/read-only native arguments only; no append bypass')
    for key in ('prepared', 'analysis_gate'):
        args[key] = copy.deepcopy(args[key])
    if not all(callable(x) for x in (read_checkpoint, write_checkpoint,
                                     verify_assignment, args['request'])):
        raise ValueError('Trusted fresh ports required')
    binding = expected_binding(args)  # validates complete evidence before ports
    gate = args['analysis_gate']
    desired = ('NEXUS_SOURCE_PAGE=' + args['source_page'] + '\nNEXUS_SOURCE_SHA256='
               + args['source_sha256'] + '\n' + args['analysis'])
    if (gate['binding']['source_id'] != args['source_page']
            or gate['binding']['source_sha256'] != args['source_sha256']
            or gate['binding']['output_id'] != args['output_name']
            or gate['report']['output_text'] != desired
            or type(args['allow_create']) is not bool):
        raise ValueError('Exact source/output gate required')
    path = Path(args['journal_path']).resolve()
    if Path(args['journal_path']).is_symlink():
        raise ValueError('Regular journal required')
    assignment = dict(mode='OWNER_INVOKED_SUPERVISED',
        transaction_id=ctx['transaction_id'], assignment_id=ctx['assignment_id'],
        actor=ctx['actor'])

    def assigned():
        if verify_assignment(copy.deepcopy(assignment)) != assignment:
            raise PermissionError('Current exclusive owner-invoked assignment required')

    # No original transcript chunks are copied to the remote checkpoint.
    identity = dict(context=ctx, journal_path=str(path), native_binding_sha256=
        hashlib.sha256(binding.encode()).hexdigest(), source_page=args['source_page'],
        source_sha256=args['source_sha256'], source_receipt=args['prepared']['receipt'],
        output_name=args['output_name'], expected_owner=args['expected_owner'],
        desired_content=desired, analysis_gate=gate)
    intent = dict(schema='nexus.supervised-checkpoint.v1', identity=identity, state='INTENT')
    request = args['request']
    with open(str(path) + '.checkpoint.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assigned()
        prior = copy.deepcopy(read_checkpoint(ctx['transaction_id']))
        if prior is not None:
            if (type(prior) is not dict or prior.get('schema') != intent['schema']
                    or prior.get('identity') != identity
                    or prior.get('state') not in ('INTENT', 'RECEIPT')
                    or set(prior) != (set(intent) if prior['state'] == 'INTENT'
                                      else set(intent) | {'execution'})):
                raise ValueError('Checkpoint binding/state changed; HOLD')
        if not path.is_file() and prior is not None:
            raise ValueError('Lost local journal; HOLD, never reconstruct')
        if initialize:
            if path.exists() or prior is not None:
                raise ValueError('Cannot reinitialize existing intent')
        elif not path.is_file():
            raise ValueError('Existing native journal required')
        if path.is_file():
            state, _ = _inspect(_snapshot(path), binding)
            if prior is not None and state == 'PREPARED':
                raise ValueError('Remote intent lacks native intent; HOLD')
            if prior is None and state != 'PREPARED':
                raise ValueError('Native effect lacks retained intent; HOLD')

        def checked_write(value, expected):
            assigned()
            if read_checkpoint(ctx['transaction_id']) != expected:
                raise ValueError('Checkpoint changed; HOLD (not CAS)')
            write_checkpoint(ctx['transaction_id'], copy.deepcopy(value))
            if read_checkpoint(ctx['transaction_id']) != value:
                raise ValueError('Independent checkpoint readback mismatch; HOLD')

        last_source = None

        def dispatch(operation, payload):
            nonlocal prior, last_source
            if operation == 'cortex_create':
                assigned()
                if _inspect(_snapshot(path), binding)[0] != 'INTENT':
                    raise ValueError('Native committed intent required')
                if prior is not None:
                    raise PermissionError('Prior remote intent cannot release another create')
                checked_write(intent, None)
                prior = copy.deepcopy(intent)
                # Retention may take time; reject any changed source or target.
                observed = request('archive_read', dict(page_id=args['source_page'],
                    source_sha256=args['source_sha256']))
                if last_source is None or observed != last_source:
                    raise ValueError('Source changed after retained intent')
                if request('cortex_get', dict(name=args['output_name'])) is not None:
                    raise ValueError('Destination appeared after retained intent')
                if read_checkpoint(ctx['transaction_id']) != intent:
                    raise ValueError('Intent changed before dispatch')
                assigned()
            value = request(operation, payload)
            if operation == 'archive_read':
                last_source = copy.deepcopy(value)
            return value

        execution = execute_supervised(**dict(args, request=dispatch))
        matched = (execution['handoff']['status'] == 'READBACK_MATCHED'
                   and execution.get('analysis_evidence_status') == 'STRUCTURAL_READBACK_MATCHED')
        if not matched:
            return dict(status='HOLD', execution=execution, transaction_complete=False)
        if prior is None:
            # Existing exact provider object is not adopted without prior intent.
            return dict(status='HOLD_NO_RETAINED_INTENT', execution=execution,
                        transaction_complete=False)
        receipt = dict(intent, state='RECEIPT', execution=execution)
        if prior['state'] == 'RECEIPT':
            old = dict(prior['execution'], create_requests=execution['create_requests'])
            if old != execution:
                raise ValueError('Retained execution changed; HOLD')
            receipt = prior
        else:
            checked_write(receipt, prior)
        assigned()
        if read_checkpoint(ctx['transaction_id']) != receipt:
            raise ValueError('Retained receipt changed; HOLD')
        fresh = execute_supervised(**dict(args, request=request, allow_create=False))
        if dict(execution, create_requests=fresh['create_requests']) != fresh:
            raise ValueError('Provider output changed after receipt; HOLD')
        return dict(status='SUPERVISED_RECEIPT_READBACK_MATCHED', execution=fresh,
                    checkpoint_sha256=_digest(receipt), transaction_complete=True,
                    unattended_acceptance=False, remote_fencing=False)
