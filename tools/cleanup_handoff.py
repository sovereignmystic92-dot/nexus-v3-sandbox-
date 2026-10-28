"""Single-worker cleanup intent journal; no removal or provider access itself.

Custody must outlive the worker/resources being cleaned. SQLite FULL commits
do not establish survival of host loss. Callers validate ownership and provide
truthful removal/observation callbacks; this is not remote ownership fencing.
"""
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3


class Hold(RuntimeError):
    pass


def encode(plan):
    if (type(plan) is not dict or set(plan) != {'run_id', 'source_sha', 'steps'}
            or any(not isinstance(plan[k], str) or not plan[k]
                   for k in ('run_id', 'source_sha'))
            or type(plan['steps']) is not list or not plan['steps']):
        raise ValueError('Complete cleanup plan required')
    names = set()
    for step in plan['steps']:
        if (type(step) is not dict or set(step) != {'action', 'target'}
                or any(not isinstance(v, str) or not v or len(v) > 4096
                       for v in step.values()) or step['action'] in names):
            raise ValueError('Unique bounded actions and exact targets required')
        names.add(step['action'])
    return json.dumps(plan, sort_keys=True, separators=(',', ':'))


class Journal:
    @classmethod
    def create(cls, path, plan):
        encoded = encode(plan)
        path = Path(path)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with closing(sqlite3.connect(path)) as db, db:
            db.execute('PRAGMA synchronous=FULL')
            db.executescript('''
                CREATE TABLE binding (plan TEXT NOT NULL);
                CREATE TABLE steps (position INTEGER PRIMARY KEY,
                    action TEXT UNIQUE NOT NULL, state TEXT NOT NULL,
                    attempts INTEGER NOT NULL);
                CREATE TABLE events (sequence INTEGER PRIMARY KEY,
                    action TEXT NOT NULL, state TEXT NOT NULL, at TEXT NOT NULL);
            ''')
            db.execute('INSERT INTO binding VALUES (?)', (encoded,))
            db.executemany('INSERT INTO steps VALUES (?,?,?,0)',
                [(i, s['action'], 'PENDING') for i, s in enumerate(plan['steps'])])
        # Flush the directory entry used by a later process to find the journal.
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        return cls(path, plan)

    def __init__(self, path, expected_plan):
        self.path = Path(path).absolute()
        self.encoded = encode(expected_plan)
        self.plan = json.loads(self.encoded)
        self.snapshot()

    def _db(self):
        if self.path.is_symlink():
            raise Hold('Symlink journal refused')
        db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True)
        try:
            db.execute('PRAGMA synchronous=FULL')
            if db.execute('SELECT plan FROM binding').fetchall() != [(self.encoded,)]:
                raise Hold('Cleanup journal binding mismatch')
        except Exception:
            db.close()
            raise
        return db

    def _change(self, action, state, begin=False):
        self.snapshot()
        with closing(self._db()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            pending = db.execute("SELECT action,state FROM steps WHERE state!='VERIFIED' "
                                 'ORDER BY position LIMIT 1').fetchone()
            if pending is None:
                return False
            if pending[0] != action:
                raise Hold('Earlier cleanup action must be reconciled first')
            if begin and pending[1] == 'UNCERTAIN':
                raise Hold('Inspect destination; blind cleanup replay refused')
            if begin and pending[1] not in ('PENDING', 'PRESENT'):
                raise Hold('Invalid cleanup state')
            if not begin and pending[1] != 'UNCERTAIN':
                raise Hold('Only a pending intent can be observed')
            db.execute('UPDATE steps SET state=?,attempts=attempts+? WHERE action=?',
                       (state, int(begin), action))
            db.execute('INSERT INTO events(action,state,at) VALUES (?,?,?)',
                       (action, state, datetime.now(timezone.utc).isoformat()))
        return True

    def snapshot(self):
        with closing(self._db()) as db:
            if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise Hold('Journal integrity check failed')
            rows = db.execute('SELECT position,action,state,attempts FROM steps '
                              'ORDER BY position').fetchall()
            events = db.execute('SELECT sequence,action,state,at FROM events '
                                'ORDER BY sequence').fetchall()
        if (len(rows) != len(self.plan['steps']) or any(
                row[0] != i or row[1] != self.plan['steps'][i]['action']
                or row[2] not in ('PENDING', 'PRESENT', 'UNCERTAIN', 'VERIFIED')
                or type(row[3]) is not int or row[3] < 0
                for i, row in enumerate(rows))):
            raise Hold('Malformed cleanup state')
        replay = {s['action']: ['PENDING', 0] for s in self.plan['steps']}
        for index, (sequence, action, state, at) in enumerate(events, 1):
            expected = next((s['action'] for s in self.plan['steps']
                             if replay[s['action']][0] != 'VERIFIED'), None)
            if (sequence != index
                    or action != expected or not isinstance(at, str) or not at):
                raise Hold('Cleanup event sequence mismatch')
            previous, attempts = replay[action]
            if state == 'UNCERTAIN' and previous in ('PENDING', 'PRESENT'):
                replay[action] = [state, attempts + 1]
            elif state in ('VERIFIED', 'PRESENT') and previous == 'UNCERTAIN':
                replay[action] = [state, attempts]
            else:
                raise Hold('Invalid cleanup event transition')
        if any(replay[row[1]] != [row[2], row[3]] for row in rows):
            raise Hold('Cleanup events do not match current state')
        steps = [dict(self.plan['steps'][i], state=row[2], attempts=row[3])
                 for i, row in enumerate(rows)]
        pending = next((s for s in steps if s['state'] != 'VERIFIED'), None)
        return {'plan': self.plan, 'steps': steps,
                'last_verified': [s['action'] for s in steps if s['state']=='VERIFIED'],
                'next_action': None if pending is None else pending['action'],
                'next_permitted_step': 'COMPLETE' if pending is None else
                    ('INSPECT_AND_RECONCILE_ONLY' if pending['state']=='UNCERTAIN'
                     else 'VERIFY_OWNERSHIP_THEN_EXECUTE'),
                'events': [dict(zip(('sequence','action','state','at'), row))
                           for row in events]}

    def reconcile(self, action, observe):
        """Observe actual state; never dispatch a removal while reconciling."""
        pending = self.snapshot()
        if pending['next_action'] != action or pending['next_permitted_step'] != 'INSPECT_AND_RECONCILE_ONLY':
            raise Hold('No matching uncertain action')
        absent = observe()
        if type(absent) is not bool:
            raise Hold('Strict absence observation required')
        self._change(action, 'VERIFIED' if absent else 'PRESENT')
        return self.snapshot()

    def execute(self, action, remove, observe, checkpoint=lambda _: None):
        """Intent commits before action; uncertainty survives callback failure."""
        if not self._change(action, 'UNCERTAIN', begin=True):
            return self.snapshot()
        checkpoint(self.snapshot())  # Separate connection readback before action.
        remove()  # On failure/lost reply, do not retry or assume nothing happened.
        result = self.reconcile(action, observe)
        checkpoint(result)
        if result['next_action'] == action:
            raise Hold('Removal not verified; explicit scope recheck required')
        return result
