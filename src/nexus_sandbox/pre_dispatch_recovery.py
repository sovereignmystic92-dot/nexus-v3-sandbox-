"""One-shot native INTENT continuation; evidence and authority remain host-owned.

No journal reset, replacement transaction, uncertain-effect retry or scheduling.
"""
import copy
import fcntl
import hashlib
import json
import sqlite3
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate_permit(value, binding_data, binding, transaction_id):
    permit = copy.deepcopy(value)
    fields = {'transaction_id', 'permit_id', 'native_binding_sha256', 'intent_sha256',
              'source_sha256', 'output_sha256', 'analysis_evidence_sha256',
              'checkpoint_reference', 'authority_ref', 'evidence_refs', 'outcome'}
    if (type(permit) is not dict or set(permit) != fields
            or any(type(permit[k]) is not str or not permit[k].strip()
                   or len(permit[k]) > 512 for k in fields - {'evidence_refs'})
            or type(permit['evidence_refs']) is not list or not permit['evidence_refs']
            or len(permit['evidence_refs']) > 100
            or any(type(x) is not str or not x.strip() or len(x) > 512
                   for x in permit['evidence_refs'])
            or permit['outcome'] != 'CONFIRMED_PRE_DISPATCH'
            or permit['transaction_id'] != transaction_id
            or permit['native_binding_sha256'] != hashlib.sha256(binding.encode()).hexdigest()
            or any(permit[k] != binding_data[k] for k in
                   ('source_sha256', 'output_sha256', 'analysis_evidence_sha256'))
            or len(permit['intent_sha256']) != 64
            or any(c not in '0123456789abcdef' for c in permit['intent_sha256'])):
        raise ValueError('Exact confirmed pre-dispatch permit required')
    return permit


def recover_checkpoint_supervised(*, context, supervised_kwargs, original_intent,
        permit, read_checkpoint, read_recovery, append_recovery, verify_authority,
        verify_assignment, reconcile_only=False):
    """Trusted ports freshly authenticate original intent, positive non-dispatch
    evidence, owner authority/assignment and append-only recovery record custody.

    No original intent write port exists. JSON wire lists are canonicalized only
    for comparison/digest; native analysis gate still requires the exact tuple.
    """
    from .supervised_journal_custody import expected_binding, _inspect, _snapshot
    from .transcript_supervised_host import _execute_supervised, execute_supervised
    ctx, args, intent = copy.deepcopy(context), dict(supervised_kwargs), copy.deepcopy(original_intent)
    if set(args) != {'journal_path', 'prepared', 'source_page', 'source_sha256',
                    'output_name', 'analysis', 'expected_owner', 'request',
                    'allow_create', 'analysis_gate'}:
        raise ValueError('Exact create-only gated arguments required')
    for k in ('prepared', 'analysis_gate'):
        args[k] = copy.deepcopy(args[k])
    binding = expected_binding(args)
    gate = args['analysis_gate']
    desired = ('NEXUS_SOURCE_PAGE=' + args['source_page'] + '\nNEXUS_SOURCE_SHA256='
               + args['source_sha256'] + '\n' + args['analysis'])
    if (type(ctx) is not dict or set(ctx) != {'transaction_id','assignment_id','actor',
            'source_revision','code_revision','policy_revision','destination'}
            or any(type(ctx[k]) is not str or not ctx[k].strip() for k in ctx if k != 'destination')
            or type(ctx['destination']) is not dict
            or set(ctx['destination']) != {'parent', 'dependencies'}
            or type(reconcile_only) is not bool
            or args['allow_create'] is not (not reconcile_only)
            or gate['binding']['run_id'] != ctx['transaction_id']
            or gate['binding']['source_id'] != args['source_page']
            or gate['binding']['source_sha256'] != args['source_sha256']
            or gate['binding']['output_id'] != args['output_name']
            or gate['report']['output_text'] != desired):
        raise ValueError('Exact original transaction context and source/output gate required')
    data = json.loads(binding)
    pinned = validate_permit(permit, data, binding, ctx['transaction_id'])
    path = Path(args['journal_path'])
    identity = dict(context=ctx, journal_path=str(path.resolve()),
        native_binding_sha256=hashlib.sha256(binding.encode()).hexdigest(),
        source_page=args['source_page'], source_sha256=args['source_sha256'],
        source_receipt=args['prepared']['receipt'], output_name=args['output_name'],
        expected_owner=args['expected_owner'], desired_content=desired, analysis_gate=gate)
    expected_intent = dict(schema='nexus.supervised-checkpoint.v1', identity=identity, state='INTENT')
    if digest(intent) != digest(expected_intent) or digest(intent) != pinned['intent_sha256']:
        raise ValueError('Original retained INTENT must remain exact')
    if (not all(callable(x) for x in (args['request'],read_checkpoint,read_recovery,
                                      append_recovery,verify_authority,verify_assignment))
            or path.is_symlink() or not path.is_file()):
        raise ValueError('Existing journal and trusted ports required; lost journal HOLD')
    tx = ctx['transaction_id']
    assignment = dict(mode='OWNER_INVOKED_SUPERVISED', transaction_id=tx,
                       assignment_id=ctx['assignment_id'], actor=ctx['actor'])
    def authorize():
        if verify_assignment(copy.deepcopy(assignment)) != assignment:
            raise PermissionError('Owner-invoked exclusive assignment required')
        if verify_authority(copy.deepcopy(pinned)) != pinned:
            raise PermissionError('Positive reviewed non-dispatch evidence required')
        if digest(read_checkpoint(tx)) != pinned['intent_sha256']:
            raise ValueError('Original intent changed')
    request = args['request']
    authorization = dict(event='AUTHORIZED', permit=pinned)
    started = dict(event='DISPATCH_STARTED', permit_sha256=digest(pinned))
    # Same companion lock as ordinary checkpoint host; native host takes its own
    # flock before consuming the one-shot recovery row.
    with open(str(path) + '.checkpoint.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        authorize()
        native_state, _ = _inspect(_snapshot(path), binding)
        history = copy.deepcopy(read_recovery(tx))
        if reconcile_only:
            if native_state not in ('INTENT', 'VERIFIED') or (history != [authorization, started]
                    and not (type(history) is list and len(history) == 3
                             and history[:2] == [authorization, started]
                             and type(history[2]) is dict
                             and set(history[2]) == {'event', 'execution'}
                             and history[2]['event'] == 'RECEIPT')):
                raise ValueError('Exact consumed recovery history required')
            with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
                consumed = db.execute('SELECT permit FROM recovery_attempt WHERE singleton=1').fetchall()
            if consumed != [(json.dumps(pinned, sort_keys=True),)]:
                raise ValueError('Matching native permit consumption required')
        else:
            if native_state != 'INTENT':
                raise ValueError('Preserved native INTENT required')
            if history != []:
                raise PermissionError('Prior recovery exists; reconcile read-only')
            if request('cortex_get', dict(name=args['output_name'])) is not None:
                raise ValueError('Destination exists; reconcile without recovery create')
            append_recovery(tx, copy.deepcopy(authorization))
            if read_recovery(tx) != [authorization]:
                raise ValueError('Recovery authorization readback failed; HOLD')
        last_source = None
        def dispatch(operation, payload):
            nonlocal last_source
            if operation == 'cortex_create':
                # Native recovery permit is already consumed durably here.
                authorize()
                if read_recovery(tx) != [authorization]:
                    raise ValueError('Recovery record changed')
                append_recovery(tx, copy.deepcopy(started))
                if read_recovery(tx) != [authorization, started]:
                    raise ValueError('Dispatch-start retention failed; HOLD')
                observed = request('archive_read', dict(page_id=args['source_page'],
                                                       source_sha256=args['source_sha256']))
                if last_source is None or observed != last_source:
                    raise ValueError('Source changed before recovery dispatch')
                if request('cortex_get', dict(name=args['output_name'])) is not None:
                    raise ValueError('Destination appeared before recovery dispatch')
                authorize()
            value = request(operation, payload)
            if operation == 'archive_read': last_source = copy.deepcopy(value)
            return value
        if reconcile_only:
            execution = execute_supervised(**args)
        else:
            def verify_recovery(candidate):
                if candidate == pinned:
                    authorize()
                    return copy.deepcopy(pinned)

            execution = _execute_supervised(**dict(args, request=dispatch),
                recovery_authorization=pinned, verify_recovery=verify_recovery)
        if (execution['handoff']['status'] != 'READBACK_MATCHED'
                or execution.get('analysis_evidence_status') != 'STRUCTURAL_READBACK_MATCHED'):
            return dict(status='HOLD', transaction_complete=False, execution=execution)
        current = copy.deepcopy(read_recovery(tx))
        receipt = dict(event='RECEIPT', execution=execution)
        if reconcile_only and len(history) == 3:
            if (current != history or dict(history[2]['execution'],
                    create_requests=execution['create_requests']) != execution):
                raise ValueError('Retained recovery receipt changed')
            receipt = history[2]
        else:
            if current != [authorization, started]:
                raise ValueError('Recovery history changed before receipt')
            append_recovery(tx, copy.deepcopy(receipt))
        if read_recovery(tx) != [authorization, started, receipt]:
            raise ValueError('Recovery receipt readback failed')
        authorize()
        fresh = execute_supervised(**dict(args, request=request, allow_create=False))
        if dict(execution, create_requests=fresh['create_requests']) != fresh:
            raise ValueError('Output/source changed after receipt')
        return dict(status='RECOVERY_RECEIPT_READBACK_MATCHED', transaction_complete=True,
                    execution=fresh, original_intent_preserved=True,
                    unattended_acceptance=False, remote_fencing=False)
