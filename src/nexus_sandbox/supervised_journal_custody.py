"""Opt-in single-worker journal custody; storage/authentication are host ports.

No credentials, connector implementation, retries, scheduler or remote fencing.
The authoritative head must use atomic compare-and-swap in protected storage.
"""
import base64
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from .analysis_evidence import validate_analysis_evidence
from .transcript_supervised_host import execute_supervised

LIMIT = 16 * 1024 * 1024
SCHEMA = 'nexus.supervised-journal-custody.v1'


def _hash(content):
    return hashlib.sha256(content).hexdigest()


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def _text(value):
    return type(value) is str and 0 < len(value) <= 512 and value == value.strip()


def _head(value):
    if value is None:
        return
    if (type(value) is not dict or set(value) != {'generation', 'reference', 'sha256'}
            or type(value['generation']) is not int or value['generation'] < 1
            or not _text(value['reference']) or type(value['sha256']) is not str
            or len(value['sha256']) != 64
            or any(c not in '0123456789abcdef' for c in value['sha256'])):
        raise ValueError('Invalid custody head')


def _inspect(content, binding):
    if type(content) is not bytes or not 0 < len(content) <= LIMIT:
        raise ValueError('Invalid journal bytes')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'inspect.sqlite'
        path.write_bytes(content)
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
            if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('Journal integrity failure')
            rows = db.execute('SELECT singleton,binding,state,module_id FROM execution').fetchall()
    if (len(rows) != 1 or rows[0][0] != 1 or rows[0][1] != binding
            or rows[0][2] not in ('PREPARED', 'INTENT', 'VERIFIED')
            or (rows[0][2] == 'VERIFIED' and not _text(rows[0][3]))
            or (rows[0][2] != 'VERIFIED' and rows[0][3] is not None)):
        raise ValueError('Journal binding/state mismatch')
    return rows[0][2], rows[0][3]


def _snapshot(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Existing regular journal required')
    # SQLite backup includes committed WAL pages; copying only the main file
    # would lose intent on a host that selected WAL mode.
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / 'snapshot.sqlite'
        with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(target)) as destination:
                source.backup(destination)
        return target.read_bytes()


class JournalCustody:
    """Ports: retain(bytes)->ref; read(ref)->bytes; head(key)->head|None;
    cas(key, expected_head, new_head)->exact bool. None means proven absence.

    Retain/read must be independent private durable operations. The host owns
    account grants and an authoritative, non-rollbackable key-to-head mapping.
    A local mirror or read-then-write implementation is not an atomic CAS.
    """

    def __init__(self, key, binding, *, retain, read, head, cas):
        if not _text(key) or type(binding) is not str or not binding:
            raise ValueError('Custody key and exact binding required')
        self.key, self.binding = key, binding
        self.retain, self.read, self.head, self.cas = retain, read, head, cas

    def current(self):
        value = self.head(self.key)
        _head(value)
        # Freeze host-owned mutable structures across subsequent callbacks.
        return json.loads(_json(value))

    def load(self, head):
        _head(head)
        if head is None:
            raise ValueError('Missing custody head; reconcile, never reset')
        content = self.read(head['reference'])
        if type(content) is not bytes or len(content) > LIMIT * 2 or _hash(content) != head['sha256']:
            raise ValueError('Custody object readback mismatch')
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError('Duplicate custody field')
                result[key] = value
            return result
        obj = json.loads(content, object_pairs_hook=pairs)
        if (type(obj) is not dict or set(obj) != {'schema', 'key', 'binding',
                'generation', 'previous', 'journal_sha256', 'journal_b64'}
                or obj['schema'] != SCHEMA or obj['key'] != self.key
                or obj['binding'] != self.binding
                or type(obj['generation']) is not int
                or obj['generation'] != head['generation']):
            raise ValueError('Custody envelope binding mismatch')
        _head(obj['previous'])
        if ((obj['generation'] == 1 and obj['previous'] is not None)
                or (obj['generation'] > 1 and (obj['previous'] is None
                    or obj['previous']['generation'] != obj['generation'] - 1))):
            raise ValueError('Custody predecessor mismatch')
        journal = base64.b64decode(obj['journal_b64'], validate=True)
        if _hash(journal) != obj['journal_sha256']:
            raise ValueError('Custody journal digest mismatch')
        _inspect(journal, self.binding)
        return journal

    def checkpoint(self, path, previous):
        if self.current() != previous:
            raise ValueError('Custody head changed; reconcile')
        journal = _snapshot(path)
        state, module_id = _inspect(journal, self.binding)
        if previous is not None:
            prior_state, prior_module = _inspect(self.load(previous), self.binding)
            order = {'PREPARED': 0, 'INTENT': 1, 'VERIFIED': 2}
            if order[state] < order[prior_state] or (prior_module and module_id != prior_module):
                raise ValueError('Journal rollback or identity change')
        obj = dict(schema=SCHEMA, key=self.key, binding=self.binding,
                   generation=1 if previous is None else previous['generation'] + 1,
                   previous=previous, journal_sha256=_hash(journal),
                   journal_b64=base64.b64encode(journal).decode('ascii'))
        content = _json(obj)
        reference = self.retain(content)
        if not _text(reference) or self.read(reference) != content:
            raise ValueError('Independent retained-object readback required')
        new = dict(generation=obj['generation'], reference=reference, sha256=_hash(content))
        if self.cas(self.key, previous, new) is not True:
            raise ValueError('Custody CAS failed; reconcile')
        if self.current() != new:
            raise ValueError('Custody pointer readback mismatch')
        self.load(new)
        return new

    def restore(self, path):
        """Explicit restore to a missing path only; never grants create authority."""
        head = self.current()
        journal = self.load(head)
        if self.current() != head:
            raise ValueError('Custody head changed during restore')
        path = Path(path)
        # Exclusive creation refuses files and symlinks. Caller must use this
        # same allocated path for the native host, under single-worker custody.
        with path.open('xb') as stream:
            os.chmod(path, 0o600)
            stream.write(journal)
            stream.flush()
            os.fsync(stream.fileno())
        if path.read_bytes() != journal:
            raise ValueError('Restored journal byte mismatch')
        _inspect(path.read_bytes(), self.binding)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return head


def expected_binding(arguments):
    """Same native binding, including the full structural evidence fingerprint."""
    gate = arguments['analysis_gate']
    fingerprint = validate_analysis_evidence(gate['binding'], gate['required_domains'], gate['report'])
    desired = ('NEXUS_SOURCE_PAGE=' + arguments['source_page'] + '\nNEXUS_SOURCE_SHA256='
               + arguments['source_sha256'] + '\n' + arguments['analysis'])
    return json.dumps(dict(prepared=arguments['prepared'],
        source_page=arguments['source_page'], source_sha256=arguments['source_sha256'],
        output_name=arguments['output_name'], output_sha256=_hash(desired.encode()),
        expected_owner=arguments['expected_owner'], analysis_evidence_sha256=fingerprint), sort_keys=True)


def execute_custodied_supervised(*, custody, initialize=False, **arguments):
    """Delegate to the mandatory-gated host; custody failures forbid creates.

    initialize=True is only for an explicitly authorized new transaction, not
    recovery. Existing/lost journals require retained-head reconciliation.
    """
    return _execute(custody, initialize, arguments, execute_supervised)


def execute_custodied_connected(*, custody, plan, consumer, supervised_kwargs,
                               read_source_reference, read_retained_receipt,
                               initialize=False):
    """Preserve the opt-in connected host's separate retained-receipt gate."""
    from .connected_supervised_host import execute_connected_supervised

    def runner(**arguments):
        return execute_connected_supervised(plan=plan, consumer=consumer,
            supervised_kwargs=arguments, read_source_reference=read_source_reference,
            read_retained_receipt=read_retained_receipt)

    return _execute(custody, initialize, dict(supervised_kwargs), runner)


def _execute(custody, initialize, arguments, runner):
    if type(initialize) is not bool or custody.binding != expected_binding(arguments):
        raise ValueError('Exact custody/native binding required')
    path = Path(arguments['journal_path'])
    previous = custody.current()
    if initialize:
        if previous is not None or path.exists() or path.is_symlink():
            raise ValueError('New custody cannot replace existing transaction')
    else:
        if previous is None or not path.is_file() or path.is_symlink():
            raise ValueError('Restore/reconcile existing custody first')
        local_state = _inspect(_snapshot(path), custody.binding)
        retained_state = _inspect(custody.load(previous), custody.binding)
        if local_state != retained_state:
            raise ValueError('Local/retained state differs; explicitly reconcile')
    request = arguments['request']
    first = True

    def guarded_request(operation, payload):
        nonlocal previous, first
        if first or operation == 'cortex_create':
            # The native flock is held here. Native INTENT is committed before
            # cortex_create reaches this callback. Never dispatch on failure.
            if operation == 'cortex_create' and _inspect(_snapshot(path), custody.binding)[0] != 'INTENT':
                raise ValueError('Committed INTENT required')
            previous = custody.checkpoint(path, previous)
            first = False
        return request(operation, payload)

    arguments['request'] = guarded_request
    result = runner(**arguments)
    previous = custody.checkpoint(path, previous)
    return dict(execution=result, custody_head=previous,
                custody_status='JOURNAL_READBACK_MATCHED', remote_fencing=False,
                live_provider_authorization=False)
