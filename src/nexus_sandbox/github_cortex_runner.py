"""Persistent synthetic event consumer; no network, scheduler or credential lookup.

Host owns authenticated GitHub observations, scoped Cortex callbacks and durable
private storage. A callback must never treat a read outage as absence.
"""
from contextlib import closing, contextmanager
from dataclasses import asdict
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from .cortex_adapter import CortexAdapter, Module, MARKER, valid_module
from .cortex_host_transport import CortexHostTransport
from .github_cortex_bridge import make_fixture
from .github_cortex_event import normalize_run


class ExecutionRunner:
    @classmethod
    def initialize(cls, path, identity, **options):
        """Explicit provisioning only; never replace a lost/existing journal."""
        if type(identity) is not str or not identity:
            raise ValueError('Explicit journal identity required')
        config = json.dumps(dict(source=asdict(options['source']),
                                 prefix=options['target_prefix']), sort_keys=True)
        path = Path(path)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with closing(sqlite3.connect(path)) as db, db:
            db.execute('CREATE TABLE runner_identity (identity TEXT, config TEXT)')
            db.execute('INSERT INTO runner_identity VALUES (?,?)', (identity, config))
            db.execute('CREATE TABLE runner_inbox (key TEXT PRIMARY KEY, run TEXT NOT NULL, state TEXT NOT NULL)')
        return cls(path, identity, **options)

    def __init__(self, path, identity, *, source, target_prefix, transport,
                 observe_run, fixture_execution=False):
        if (type(source) is not Module or not valid_module(source)
                or not source.name.startswith('Nexus Sandbox ')
                or not source.content.startswith(MARKER)
                or type(target_prefix) is not str
                or not target_prefix.startswith('Nexus Sandbox ')
                or len(target_prefix) > 120 or source.name.startswith(target_prefix)
                or type(transport) is not CortexHostTransport
                or not callable(observe_run) or type(fixture_execution) is not bool):
            raise ValueError('Explicit synthetic host bindings required')
        self.path = Path(path).resolve()
        self.source, self.prefix = source, target_prefix
        self.transport, self.observe_run = transport, observe_run
        self.enabled = fixture_execution
        self.identity = identity
        self.config = json.dumps(dict(source=asdict(source), prefix=target_prefix), sort_keys=True)
        with self._lock(), closing(self._db()) as db, db:
            rows = db.execute('SELECT identity,config FROM runner_identity').fetchall()
            if len(rows) != 1 or rows[0][0] != identity or not identity:
                raise ValueError('Journal identity mismatch')
            if rows[0][1] != self.config:
                raise ValueError('Runner binding changed; hold')

    def _db(self):
        db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True)
        db.execute('PRAGMA synchronous=FULL')
        rows = db.execute('SELECT identity,config FROM runner_identity').fetchall()
        if len(rows) != 1 or rows[0][0] != self.identity or rows[0][1] != self.config:
            db.close()
            raise ValueError('Journal binding unavailable')
        return db

    @contextmanager
    def _lock(self):
        fd = os.open(str(self.path) + '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(fd)

    def _verified_run(self, run):
        expected = normalize_run(run)
        fresh = self.observe_run(expected['run_id'], expected['attempt'])
        if normalize_run(fresh) != expected:
            raise ValueError('GitHub observation differs; hold')
        # Persist only the fixed, normalized fields; never arbitrary webhook data.
        return dict(id=expected['run_id'], run_attempt=expected['attempt'],
                    workflow_id=expected['workflow_id'], head_sha=expected['commit_sha'],
                    conclusion=expected['conclusion'], status='completed',
                    repository={'full_name': expected['repository']}, html_url=expected['run_url'])

    def enqueue(self, run):
        """Host event entry point. Webhook data alone supplies no authority."""
        with self._lock():
            verified = self._verified_run(run)
            key = normalize_run(verified)['event_key']
            body = json.dumps(verified, sort_keys=True)
            with closing(self._db()) as db, db:
                prior = db.execute('SELECT run FROM runner_inbox WHERE key=?', (key,)).fetchone()
                if prior and prior != (body,):
                    raise ValueError('Event identity already bound to different content')
                db.execute('INSERT OR IGNORE INTO runner_inbox VALUES (?,?,?)', (key, body, 'PENDING'))
        return key

    def handle_event(self, run):
        key = self.enqueue(run)
        return self.process(key)

    def process(self, key):
        if not self.enabled:
            return 'DISABLED'
        with self._lock():
            with closing(self._db()) as db:
                row = db.execute('SELECT run FROM runner_inbox WHERE key=?', (key,)).fetchone()
            if row is None:
                raise ValueError('Unknown event')
            status = 'HOLD'
            try:
                run = self._verified_run(json.loads(row[0]))
                event = normalize_run(run)
                if event['event_key'] != key:
                    raise ValueError('Corrupt event identity')
                token = hashlib.sha256(key.encode()).hexdigest()
                target = self.prefix + token
                request = make_fixture(run, self.source, target, 'synthetic:request:' + token)
                adapter = CortexAdapter(self.path, frozenset((self.source.name, target)), self.transport)
                outcome = adapter.ensure(request)
                if outcome.protocol_verdict == 'VERIFIED':
                    status = 'VERIFIED'
            except Exception:
                # Never emit callback details or retry writes after uncertain intent.
                status = 'HOLD'
            with closing(self._db()) as db, db:
                db.execute('UPDATE runner_inbox SET state=? WHERE key=?', (status, key))
            return status

    def recover(self, limit=100):
        """Bounded restart drain; HOLD entries reconcile via existing adapter intent."""
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('Bounded recovery required')
        with self._lock(), closing(self._db()) as db:
            keys = [r[0] for r in db.execute(
                "SELECT key FROM runner_inbox WHERE state IN ('PENDING','HOLD') ORDER BY rowid LIMIT ?", (limit,))]
        return {key: self.process(key) for key in keys}
