"""Durable solution handoffs with explicit delivery and acceptance receipts.

This module installs no scheduler, provider client, credential, or authority.  An
authorized host may call ``deliver_one`` with a bounded delivery callback.  The
outbox commits routing intent before that callback and never blindly retries an
uncertain delivery.
"""
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3


class HandoffHold(RuntimeError):
    """The saved state requires reconciliation or a valid next transition."""


@dataclass(frozen=True)
class Handoff:
    finding_id: str
    source_ref: str
    source_revision: str
    destination: str
    next_action: str
    completion_criteria: tuple[str, ...]
    authorization_ref: str
    priority: int


TRANSITIONS = {
    'RECORDED': {'ROUTING', 'BLOCKED'},
    'ROUTING': {'ROUTED', 'BLOCKED'},
    'ROUTED': {'ACCEPTED', 'BLOCKED'},
    'ACCEPTED': {'IN_PROGRESS', 'BLOCKED'},
    'IN_PROGRESS': {'VERIFIED_COMPLETE', 'BLOCKED'},
    'BLOCKED': {'RECORDED'},
    'VERIFIED_COMPLETE': set(),
}


def _require(condition, message='Invalid handoff or receipt'):
    if not condition:
        raise ValueError(message)


def _text(value, limit=2048):
    return type(value) is str and bool(value.strip()) and len(value) <= limit


def _time(value):
    _require(_text(value, 64), 'Bounded observation time required')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('ISO-8601 observation time required') from exc
    _require(parsed.tzinfo is not None, 'UTC-offset observation time required')


def encode(handoff):
    _require(type(handoff) is Handoff)
    values = asdict(handoff)
    _require(all(_text(values[key]) for key in (
        'finding_id', 'source_ref', 'source_revision', 'destination',
        'next_action', 'authorization_ref')))
    _require(type(handoff.completion_criteria) is tuple
             and 0 < len(handoff.completion_criteria) <= 20
             and len(set(handoff.completion_criteria)) == len(handoff.completion_criteria)
             and all(_text(item) for item in handoff.completion_criteria))
    _require(type(handoff.priority) is int and 1 <= handoff.priority <= 100)
    values['completion_criteria'] = list(handoff.completion_criteria)
    return json.dumps(values, sort_keys=True, separators=(',', ':'))


def handoff_id(handoff):
    return hashlib.sha256(encode(handoff).encode()).hexdigest()


class HandoffOutbox:
    """Single-worker local custody for actionable handoff receipts.

    The caller owns durable storage, event authentication, destination identity,
    authorization, and external readback.  SQLite serialization is not provider
    fencing or cross-host custody.
    """
    @classmethod
    def initialize(cls, path, identity):
        _require(_text(identity, 512), 'Explicit outbox identity required')
        path = Path(path)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with closing(sqlite3.connect(path)) as db, db:
            db.executescript('''
                CREATE TABLE outbox_identity (value TEXT NOT NULL);
                CREATE TABLE handoffs (
                    handoff_id TEXT PRIMARY KEY,
                    finding_id TEXT NOT NULL UNIQUE,
                    binding TEXT NOT NULL,
                    state TEXT NOT NULL,
                    blocker TEXT,
                    reopen_trigger TEXT);
                CREATE TABLE events (
                    event_id TEXT PRIMARY KEY,
                    handoff_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    evidence_ref TEXT,
                    readback_ref TEXT,
                    observed_at_utc TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    UNIQUE(handoff_id, seq));
            ''')
            db.execute('INSERT INTO outbox_identity VALUES (?)', (identity,))
        return cls(path, identity)

    def __init__(self, path, identity):
        self.path = Path(path).resolve()
        self.identity = identity
        with closing(self._db()) as db:
            rows = db.execute('SELECT value FROM outbox_identity').fetchall()
            if rows != [(identity,)] or not identity:
                raise HandoffHold('Outbox identity mismatch; restore trusted custody')

    def _db(self):
        db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True)
        db.execute('PRAGMA synchronous=FULL')
        db.execute('PRAGMA busy_timeout=5000')
        return db

    @staticmethod
    def _row(db, value):
        hid = handoff_id(value)
        row = db.execute(
            'SELECT finding_id,binding,state,blocker,reopen_trigger FROM handoffs '
            'WHERE handoff_id=?', (hid,)).fetchone()
        if row is not None and row[1] != encode(value):
            raise HandoffHold('Handoff binding changed')
        conflict = db.execute(
            'SELECT handoff_id,binding FROM handoffs WHERE finding_id=?',
            (value.finding_id,)).fetchone()
        if conflict is not None and conflict != (hid, encode(value)):
            raise HandoffHold('Finding identity reused with a different binding')
        return hid, row

    @staticmethod
    def _event(db, event_id):
        return db.execute(
            'SELECT handoff_id,from_state,to_state,actor,evidence_ref,readback_ref,'
            'observed_at_utc,detail FROM events WHERE event_id=?',
            (event_id,)).fetchone()

    def record(self, value, *, event_id, actor, observed_at_utc):
        binding = encode(value)
        _require(_text(event_id) and _text(actor))
        _time(observed_at_utc)
        hid = handoff_id(value)
        detail = '{}'
        expected = (hid, None, 'RECORDED', actor, None, None,
                    observed_at_utc, detail)
        with closing(self._db()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            prior_event = self._event(db, event_id)
            if prior_event is not None:
                if prior_event != expected:
                    raise HandoffHold('Event identity reused with different receipt')
                return self.read(hid)
            hid, row = self._row(db, value)
            if row is not None:
                return self.read(hid)
            db.execute('INSERT INTO handoffs VALUES (?,?,?,?,NULL,NULL)',
                       (hid, value.finding_id, binding, 'RECORDED'))
            db.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (event_id, hid, 0, None, 'RECORDED', actor, None, None,
                        observed_at_utc, detail))
        return self.read(hid)

    def transition(self, hid, *, event_id, to_state, actor, observed_at_utc,
                   evidence_ref=None, readback_ref=None, blocker=None,
                   reopen_trigger=None):
        _require(_text(hid, 64) and len(hid) == 64
                 and all(c in '0123456789abcdef' for c in hid))
        _require(_text(event_id) and _text(actor) and to_state in TRANSITIONS)
        _time(observed_at_utc)
        if evidence_ref is not None:
            _require(_text(evidence_ref))
        if readback_ref is not None:
            _require(_text(readback_ref))
        if to_state == 'VERIFIED_COMPLETE':
            _require(evidence_ref is not None and readback_ref is not None
                     and evidence_ref != readback_ref,
                     'Completion requires distinct result and independent readback refs')
        if to_state == 'BLOCKED':
            _require(_text(blocker) and _text(reopen_trigger),
                     'Blocked handoff requires blocker and reopening trigger')
        else:
            _require(blocker is None and reopen_trigger is None)
        detail = json.dumps(dict(blocker=blocker, reopen_trigger=reopen_trigger),
                            sort_keys=True, separators=(',', ':'))
        with closing(self._db()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT state FROM handoffs WHERE handoff_id=?',
                             (hid,)).fetchone()
            if row is None:
                raise HandoffHold('Unknown handoff')
            current = row[0]
            if to_state in ('ROUTED', 'ACCEPTED', 'IN_PROGRESS'):
                _require(evidence_ref is not None,
                         f'{to_state} requires an attributable receipt')
            if current == 'BLOCKED' and to_state == 'RECORDED':
                _require(evidence_ref is not None,
                         'Reopening requires changed evidence or a satisfied trigger')
            expected = (hid, current, to_state, actor, evidence_ref, readback_ref,
                        observed_at_utc, detail)
            prior_event = self._event(db, event_id)
            if prior_event is not None:
                # Idempotent replay compares the original saved from-state.
                if prior_event[0] != hid or prior_event[2:] != expected[2:]:
                    raise HandoffHold('Event identity reused with different receipt')
                return self.read(hid)
            if to_state not in TRANSITIONS[current]:
                raise HandoffHold(f'Invalid transition {current}->{to_state}')
            seq = db.execute(
                'SELECT COALESCE(MAX(seq),-1)+1 FROM events WHERE handoff_id=?',
                (hid,)).fetchone()[0]
            db.execute('UPDATE handoffs SET state=?,blocker=?,reopen_trigger=? '
                       'WHERE handoff_id=?',
                       (to_state, blocker, reopen_trigger, hid))
            db.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (event_id, hid, seq, current, to_state, actor,
                        evidence_ref, readback_ref, observed_at_utc, detail))
        return self.read(hid)

    def deliver_one(self, *, actor, intent_event_id, routed_event_id,
                    observed_at_utc, deliver):
        """Route one recorded item; leave ROUTING on unknown delivery outcome."""
        _require(callable(deliver))
        candidates = self.pending(states=('RECORDED',), limit=1)
        if not candidates:
            return None
        item = candidates[0]
        hid = item['handoff_id']
        self.transition(hid, event_id=intent_event_id, to_state='ROUTING',
                        actor=actor, observed_at_utc=observed_at_utc)
        try:
            result = deliver(item['binding'])
        except Exception:
            return self.read(hid)
        if type(result) is not dict or set(result) != {'delivery_ref'} \
                or not _text(result['delivery_ref']):
            return self.read(hid)
        return self.transition(hid, event_id=routed_event_id, to_state='ROUTED',
                               actor=actor, observed_at_utc=observed_at_utc,
                               evidence_ref=result['delivery_ref'])

    def pending(self, *, states=None, destination=None, limit=100):
        states = tuple(states or ('RECORDED', 'ROUTING', 'ROUTED', 'ACCEPTED',
                                  'IN_PROGRESS', 'BLOCKED'))
        _require(0 < len(states) <= len(TRANSITIONS)
                 and all(state in TRANSITIONS for state in states))
        _require(type(limit) is int and 0 < limit <= 1000)
        if destination is not None:
            _require(_text(destination))
        with closing(self._db()) as db:
            rows = db.execute(
                'SELECT handoff_id,binding,state,blocker,reopen_trigger FROM handoffs '
                'ORDER BY json_extract(binding,"$.priority"),rowid').fetchall()
        result = []
        for hid, binding, state, blocker, trigger in rows:
            decoded = json.loads(binding)
            if state in states and (destination is None
                                    or decoded['destination'] == destination):
                result.append(dict(handoff_id=hid, binding=decoded, state=state,
                                   blocker=blocker, reopen_trigger=trigger))
            if len(result) == limit:
                break
        return result

    def read(self, hid):
        with closing(self._db()) as db:
            row = db.execute(
                'SELECT binding,state,blocker,reopen_trigger FROM handoffs '
                'WHERE handoff_id=?', (hid,)).fetchone()
            if row is None:
                raise HandoffHold('Unknown handoff')
            events = db.execute(
                'SELECT event_id,seq,from_state,to_state,actor,evidence_ref,'
                'readback_ref,observed_at_utc,detail FROM events '
                'WHERE handoff_id=? ORDER BY seq', (hid,)).fetchall()
        return dict(handoff_id=hid, binding=json.loads(row[0]), state=row[1],
                    blocker=row[2], reopen_trigger=row[3],
                    events=[dict(event_id=e[0], seq=e[1], from_state=e[2],
                        to_state=e[3], actor=e[4], evidence_ref=e[5],
                        readback_ref=e[6], observed_at_utc=e[7],
                        detail=json.loads(e[8])) for e in events])
