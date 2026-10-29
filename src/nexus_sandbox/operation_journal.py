"""Reusable write-intent bookkeeping, adapted from the synthetic Notion adapter.

This module invokes no provider and grants no external authority. One trusted
worker/journal only; all real mutations remain disabled outside this library.
"""
from contextlib import closing
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import sqlite3
from uuid import UUID

from .record_readback import Binding as ReadBinding, verify


@dataclass(frozen=True)
class Operation:
    key: str
    source_id: str
    source_revision: str
    destination_id: str
    payload_sha256: str


def encode(operation):
    if type(operation) is not Operation or any(
            not isinstance(v, str) or not v or len(v) > 2048
            for v in asdict(operation).values()):
        raise ValueError('Complete bounded operation binding required')
    UUID(operation.destination_id)
    value = operation.payload_sha256
    if len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('Lowercase SHA-256 required')
    return json.dumps(asdict(operation), sort_keys=True)


class OperationJournal:
    """Caller provisions durable private custody; never silently initialize.

    A lost journal cannot be replaced and treated as a fresh operation safely.
    identity is caller-supplied, not a cryptographic trust anchor. Complete file
    replacement/tampering and independent journals are outside these guarantees.
    """
    @classmethod
    def initialize(cls, path, identity):
        if not isinstance(identity, str) or not identity:
            raise ValueError('Explicit journal identity required')
        path = Path(path)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with closing(sqlite3.connect(path)) as db, db:
            db.executescript('''
                CREATE TABLE journal_identity (value TEXT NOT NULL);
                CREATE TABLE operations (
                    key TEXT PRIMARY KEY, binding TEXT NOT NULL,
                    state TEXT NOT NULL, record_id TEXT);
            ''')
            db.execute('INSERT INTO journal_identity VALUES (?)', (identity,))
        return cls(path, identity)

    def __init__(self, path, identity):
        self.path = Path(path).resolve()
        self.identity = identity
        with closing(self._db()) as db:
            rows = db.execute('SELECT value FROM journal_identity').fetchall()
            if rows != [(identity,)] or not identity:
                raise ValueError('Journal identity mismatch; restore trusted journal')

    def _db(self):
        # mode=rw fails if lost; it never silently creates a replacement.
        db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True)
        db.execute('PRAGMA synchronous=FULL')
        return db

    @staticmethod
    def _row(db, operation):
        binding = encode(operation)
        row = db.execute('SELECT binding,state,record_id FROM operations WHERE key=?',
                         (operation.key,)).fetchone()
        if row is not None and row[0] != binding:
            raise ValueError('Operation key already bound to different intent')
        return row

    def begin(self, operation):
        """First call commits intent; every repeat requires reconciliation.

        MAY_ATTEMPT_WRITE is bookkeeping only, not provider authorization. A
        crash even before sending a write conservatively forfeits blind retry.
        """
        encoded = encode(operation)
        with closing(self._db()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, operation)
            if row is not None:
                return 'RECONCILE_ONLY'
            db.execute('INSERT INTO operations VALUES (?,?,?,NULL)',
                       (operation.key, encoded, 'WRITE_INTENT'))
        return 'MAY_ATTEMPT_WRITE'

    def acknowledge(self, operation, record_id):
        """Pin identity only; an acknowledgment is never verification."""
        record_id = UUID(record_id).hex
        with closing(self._db()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, operation)
            if row is None:
                raise ValueError('No committed intent')
            if row[2] is not None and row[2] != record_id:
                raise ValueError('Record identity changed; preserve and hold')
            db.execute('UPDATE operations SET record_id=?,state=? WHERE key=?',
                       (record_id, row[1] if row[1] == 'VERIFIED_OBSERVATION'
                        else 'ACKNOWLEDGED', operation.key))

    def reconcile(self, operation, record_id, read):
        """Reconcile an acknowledged ID or caller-discovered candidate.

        Candidate discovery completeness/duplicate absence is NOT proven here.
        No callback is invoked when the local immutable binding conflicts.
        """
        record_id = UUID(record_id).hex
        with closing(self._db()) as db:
            row = self._row(db, operation)
            if row is None:
                raise ValueError('No committed intent')
            if row[2] is not None and row[2] != record_id:
                raise ValueError('Candidate conflicts with pinned identity')
        result = verify(ReadBinding(record_id, operation.destination_id,
                                    operation.payload_sha256), read)
        with closing(self._db()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, operation)
            if row is None or (row[2] is not None and row[2] != record_id):
                raise ValueError('Journal changed; verification withheld')
            pin = record_id if result.status == 'VERIFIED_OBSERVATION' else row[2]
            db.execute('UPDATE operations SET state=?,record_id=? WHERE key=?',
                       (result.status, pin, operation.key))
        return result
