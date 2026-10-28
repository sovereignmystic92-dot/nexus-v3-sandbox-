"""Synthetic SQLite mutation-boundary reference; no provider integration.

The database serializes ownership and payload changes in the same transaction.
This is a review prototype, not authentication, a remote lease, or protection
against direct database writes. Callers must already have mutation authority.
"""
from contextlib import closing
from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3


class Held(RuntimeError):
    """Another owner already holds the synthetic target."""


class Stale(RuntimeError):
    """The supplied owner/generation no longer has write authority."""


class Stopped(RuntimeError):
    """A stopped target cannot be acquired or written."""


@dataclass(frozen=True)
class Token:
    resource_id: str
    owner: str
    generation: int


def identity(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError('A bounded nonempty identity is required')
    return value


class Boundary:
    """One explicitly provisioned synthetic target; opening never creates it."""

    @classmethod
    def initialize(cls, path, resource_id):
        identity(resource_id)
        path = Path(path)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with closing(sqlite3.connect(path)) as db, db:
            db.execute('''CREATE TABLE target (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                resource_id TEXT NOT NULL, owner TEXT,
                generation INTEGER NOT NULL CHECK(generation>=0),
                stopped INTEGER NOT NULL CHECK(stopped IN (0,1)),
                payload TEXT NOT NULL)''')
            db.execute('INSERT INTO target VALUES (1,?,NULL,0,0,?)',
                       (resource_id, ''))
        return cls(path, resource_id)

    def __init__(self, path, resource_id):
        identity(resource_id)
        path = Path(path)
        if path.is_symlink():
            raise ValueError('Symlink target refused')
        self.path = path.resolve()
        self.resource_id = resource_id
        self.snapshot()

    def _db(self):
        # A missing database must fail, rather than reset the ownership epoch.
        db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=5)
        db.execute('PRAGMA synchronous=FULL')
        return db

    def _row(self, db):
        row = db.execute('SELECT resource_id,owner,generation,stopped,payload '
                         'FROM target WHERE singleton=1').fetchone()
        if row is None or row[0] != self.resource_id:
            raise ValueError('Target identity missing or changed')
        return row

    def snapshot(self):
        with closing(self._db()) as db:
            row = self._row(db)
        return dict(zip(('resource_id', 'owner', 'generation', 'stopped',
                         'payload'), row))

    def acquire(self, owner):
        identity(owner)
        with closing(self._db()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            _, current, generation, stopped, _ = self._row(db)
            if stopped:
                raise Stopped('Target is stopped')
            if current is not None:
                raise Held('Target already has an owner')
            generation += 1
            db.execute('UPDATE target SET owner=?,generation=? WHERE singleton=1',
                       (owner, generation))
        return Token(self.resource_id, owner, generation)

    def takeover(self, expected_generation, owner):
        """Explicit trusted takeover, not automatic timeout/lease expiry."""
        identity(owner)
        if type(expected_generation) is not int or expected_generation < 1:
            raise ValueError('Expected generation required')
        with closing(self._db()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            _, current, generation, stopped, _ = self._row(db)
            if stopped:
                raise Stopped('Target is stopped')
            if current is None or generation != expected_generation:
                raise Stale('Ownership changed before takeover')
            generation += 1
            db.execute('UPDATE target SET owner=?,generation=? WHERE singleton=1',
                       (owner, generation))
        return Token(self.resource_id, owner, generation)

    def _mutate(self, token, payload=None, stop=False):
        if (type(token) is not Token or token.resource_id != self.resource_id
                or type(token.generation) is not int or token.generation < 1):
            raise Stale('Token belongs to a different target or generation')
        with closing(self._db()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            _, owner, generation, stopped, _ = self._row(db)
            if stopped:
                raise Stopped('Target is stopped')
            if owner != token.owner or generation != token.generation:
                raise Stale('Stale writer rejected before mutation')
            # Ownership validation and the mutation share one serialized commit.
            if stop:
                db.execute('UPDATE target SET stopped=1,owner=NULL,'
                           'generation=generation+1 WHERE singleton=1')
            else:
                db.execute('UPDATE target SET payload=? WHERE singleton=1',
                           (payload,))

    def write(self, token, payload):
        if not isinstance(payload, str) or len(payload) > 16384:
            raise ValueError('Bounded synthetic text required')
        self._mutate(token, payload=payload)

    def stop(self, token):
        """Revoke the current generation and preserve payload as evidence."""
        self._mutate(token, stop=True)
