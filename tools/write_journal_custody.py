"""Exact external custody of the existing SQLite write journal; no provider IO.

Host publish/fetch callbacks must save under the enrolled audit and independently
fetch the resulting artifact. An acknowledgment alone never permits dispatch.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from nexus_sandbox.approved_writes import WriteHold, content_hash

MAX_BYTES = 98304
FIELDS = {'schema', 'request_id', 'context', 'sqlite_sha256', 'sqlite_base64'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False)


def _validate_db(db, request_id, context):
    objects = db.execute("SELECT name,type FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
    if objects != [('approved_writes', 'table')]:
        raise WriteHold('Unexpected journal schema')
    if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
        raise WriteHold('Invalid journal')
    row = db.execute('SELECT intent_hash,state FROM approved_writes WHERE request_id=?',
                     (request_id,)).fetchone()
    if (row is None or row[0] != context['request_sha256']
            or row[1] not in ('DISPATCHING', 'UNCERTAIN', 'VERIFIED')):
        raise WriteHold('Custody does not bind this operation')


def snapshot(path, request_id, context):
    # mode=rw prevents silently recreating a lost local journal.
    db = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=rw', uri=True)
    try:
        _validate_db(db, request_id, context)
        raw = db.serialize()
    finally:
        db.close()
    if len(raw) > MAX_BYTES:
        raise WriteHold('Journal exceeds bounded custody size')
    return dict(schema='NXS_APPROVED_WRITE_CUSTODY_V1', request_id=request_id,
        context=json.loads(canonical(context)), sqlite_sha256=hashlib.sha256(raw).hexdigest(),
        sqlite_base64=base64.b64encode(raw).decode('ascii'))


def restore(path, envelope, *, expected_digest, request_id, context):
    """Expected digest/context must come from independently retained custody.

    Do not infer the expected digest from the supplied artifact itself. No auto
    discovery, overwrite, lost-journal initialization or trust enrollment occurs.
    """
    if (type(envelope) is not dict or set(envelope) != FIELDS
            or content_hash(envelope) != expected_digest
            or envelope['schema'] != 'NXS_APPROVED_WRITE_CUSTODY_V1'
            or envelope['request_id'] != request_id or envelope['context'] != context):
        raise WriteHold('Missing, changed or misbound custody')
    try:
        raw = base64.b64decode(envelope['sqlite_base64'], validate=True)
    except (ValueError, TypeError):
        raise WriteHold('Malformed journal bytes') from None
    if len(raw) > MAX_BYTES or hashlib.sha256(raw).hexdigest() != envelope['sqlite_sha256']:
        raise WriteHold('Changed or oversized journal bytes')
    db = sqlite3.connect(':memory:')
    try:
        db.deserialize(raw)
        _validate_db(db, request_id, context)
    except sqlite3.Error:
        raise WriteHold('Invalid saved journal') from None
    finally:
        db.close()
    # Exclusive creation: never discard an existing local journal.
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'wb') as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())


class JournalCustody:
    def __init__(self, publish, fetch):
        self.publish, self.fetch = publish, fetch
        self.last = None

    def save_verified(self, path, request_id, context):
        envelope = snapshot(path, request_id, context)
        expected = canonical(envelope)
        digest = content_hash(envelope)
        # Do not let a callback mutate the retained comparison baseline.
        identity = self.publish(json.loads(expected), digest)
        # The host must also verify artifact placement under the enrolled audit.
        if (not isinstance(identity, str) or not identity
                or canonical(self.fetch(identity)) != expected):
            raise WriteHold('External journal custody readback failed')
        self.last = dict(record_id=identity, sha256=digest)
        return dict(self.last)
