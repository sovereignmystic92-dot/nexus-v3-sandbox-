"""Opt-in single-worker write boundary with approval binding and durable intent.

Not provider-side fencing. Callbacks must be trusted bindings; direct connector
calls outside this boundary are not intercepted. Never retry an uncertain write.
"""
import hashlib
import json
import re
import sqlite3


class WriteHold(RuntimeError):
    pass


def content_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


class ApprovedWriteBoundary:
    def __init__(self, journal, authorize, read, write):
        self.journal = journal
        self.authorize, self.read, self.write = authorize, read, write
        with sqlite3.connect(journal) as db:
            db.execute('CREATE TABLE IF NOT EXISTS approved_writes '
                       '(request_id TEXT PRIMARY KEY, intent_hash TEXT NOT NULL, '
                       'state TEXT NOT NULL)')

    def execute(self, request_id, revision, destination, before_hash, payload):
        if (not isinstance(request_id, str) or not request_id or
                not isinstance(destination, str) or not destination or
                not isinstance(revision, str) or not re.fullmatch('[0-9a-f]{40}', revision) or
                not isinstance(before_hash, str) or not re.fullmatch('[0-9a-f]{64}', before_hash)):
            raise WriteHold('Exact request, revision, destination and baseline required')
        # Canonical copy prevents a caller changing the payload after approval.
        frozen = json.loads(json.dumps(payload, allow_nan=False))
        target_hash = content_hash(frozen)
        intent = {'revision': revision, 'operation': 'routine_write',
                  'destination': destination, 'before_sha256': before_hash,
                  'payload_sha256': target_hash}
        intent_hash = content_hash(intent)
        # The approval gate must bind its request_sha256 to this entire intent.
        receipt = self.authorize(dict(intent), intent_hash)
        if (not isinstance(receipt, dict) or receipt.get('verdict') != 'REVIEW_RECEIPTS_ACCEPTED'
                or receipt.get('request_sha256') != intent_hash
                or any(receipt.get(k) != intent[k] for k in ('revision', 'operation', 'destination'))):
            raise WriteHold('Current approval does not bind this exact write intent')
        with sqlite3.connect(self.journal, timeout=5) as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT intent_hash,state FROM approved_writes WHERE request_id=?',
                                  (request_id,)).fetchone()
            if existing and existing[0] != intent_hash:
                raise WriteHold('Request ID already binds a different intent')
            observed = content_hash(self.read(destination))
            if existing:
                if observed != target_hash:
                    raise WriteHold('Prior write outcome requires reconciliation; no automatic retry')
                db.execute('UPDATE approved_writes SET state=? WHERE request_id=?',
                           ('VERIFIED', request_id))
                return {'state': 'VERIFIED', 'write_attempted': False, 'request_id': request_id}
            if observed != before_hash:
                raise WriteHold('Destination changed before dispatch')
            db.execute('INSERT INTO approved_writes VALUES (?,?,?)',
                       (request_id, intent_hash, 'DISPATCHING'))
            # Intent must survive a successful remote write followed by process loss.
            db.commit()
            db.execute('BEGIN IMMEDIATE')
            try:
                self.write(destination, frozen)
                if content_hash(self.read(destination)) != target_hash:
                    raise WriteHold('Fresh read-back differs from intended content')
            except Exception:
                db.execute('UPDATE approved_writes SET state=? WHERE request_id=?',
                           ('UNCERTAIN', request_id))
                db.commit()
                raise WriteHold('Write outcome uncertain; reconcile without retry') from None
            db.execute('UPDATE approved_writes SET state=? WHERE request_id=?',
                       ('VERIFIED', request_id))
        return {'state': 'VERIFIED', 'write_attempted': True, 'request_id': request_id}

