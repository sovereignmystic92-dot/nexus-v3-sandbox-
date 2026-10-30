"""Observer-only event planning. No callbacks, credentials or live activation.

Enrollment and event provenance must be authenticated by a future host. SQLite
deduplication does not establish provider fencing or cross-host queue custody.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3


ROUTES = {
    'SOURCE_READY': 'INSPECT_TRANSCRIPT',
    'SOURCE_REVISION_CHANGED': 'INSPECT_TRANSCRIPT',
    'CHECK_FAILED': 'DIAGNOSE_CHECK',
    'JOB_INTERRUPTED': 'INSPECT_CHECKPOINT',
}


@dataclass(frozen=True)
class Event:
    event_id: str
    kind: str
    source_id: str
    revision_sha256: str
    origin: str


@dataclass(frozen=True)
class Enrollment:
    source_id: str
    policy_revision: str
    code_revision: str
    authorization_ref: str
    allowed_jobs: tuple[str, ...]
    max_jobs: int
    paused: bool = False


@dataclass(frozen=True)
class Decision:
    status: str
    job_id: str | None
    action: str | None
    reason: str


def require(condition):
    if not condition:
        raise ValueError('Malformed event or enrollment')


def validate(event, enrollment):
    require(type(event) is Event and type(enrollment) is Enrollment)
    require(all(type(x) is str and bool(x) and len(x) <= 512 for x in
                (event.event_id, event.kind, event.source_id, event.origin,
                 enrollment.source_id, enrollment.policy_revision,
                 enrollment.code_revision, enrollment.authorization_ref)))
    digest = event.revision_sha256
    require(type(digest) is str and len(digest) == 64
            and all(c in '0123456789abcdef' for c in digest))
    require(type(enrollment.allowed_jobs) is tuple
            and bool(enrollment.allowed_jobs)
            and all(type(x) is str and x in set(ROUTES.values())
                    for x in enrollment.allowed_jobs)
            and len(set(enrollment.allowed_jobs)) == len(enrollment.allowed_jobs))
    require(type(enrollment.max_jobs) is int and 0 < enrollment.max_jobs <= 1000
            and type(enrollment.paused) is bool)


class ObserverQueue:
    """Persist plans only; never mutate a source or run a selected action.

    Explicit initialization is required. Reopening missing storage holds rather
    than silently forgetting deduplication history. Use a trusted regular path.
    """
    def __init__(self, path, *, initialize=False):
        require(type(initialize) is bool)
        self.path = Path(path)
        require(not self.path.is_symlink())
        if initialize:
            # Exclusive creation prevents accidental reset of retained work.
            with self.path.open('xb'):
                pass
        require(self.path.is_file())
        with self.connect() as db:
            if initialize:
                db.execute('CREATE TABLE jobs (job_id TEXT PRIMARY KEY, binding TEXT NOT NULL)')
                db.execute('CREATE TABLE events (event_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, job_id TEXT NOT NULL)')
            else:
                require({'jobs', 'events'} <= {row[0] for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")})

    def connect(self):
        # mode=rw will not silently recreate a deleted queue.
        return sqlite3.connect(self.path.resolve().as_uri() + '?mode=rw', uri=True)

    def route(self, event, enrollment):
        validate(event, enrollment)
        action = ROUTES.get(event.kind)
        if event.origin != 'SOURCE' or action is None:
            return Decision('IGNORED', None, None, 'No enrolled source event; recursion suppressed')
        if enrollment.paused:
            return Decision('HELD', None, None, 'Enrollment paused')
        if event.source_id != enrollment.source_id or action not in enrollment.allowed_jobs:
            return Decision('HELD', None, None, 'Source or job not enrolled')
        binding = dict(source_id=event.source_id, revision_sha256=event.revision_sha256,
                       action=action, policy_revision=enrollment.policy_revision,
                       code_revision=enrollment.code_revision,
                       authorization_ref=enrollment.authorization_ref,
                       execution_mode='OBSERVE_ONLY', provider_writes=0)
        encoded = json.dumps(binding, sort_keys=True, separators=(',', ':'))
        job_id = hashlib.sha256(encoded.encode()).hexdigest()
        fingerprint = hashlib.sha256(json.dumps(vars(event), sort_keys=True).encode()).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            prior_event = db.execute('SELECT fingerprint,job_id FROM events WHERE event_id=?',
                                     (event.event_id,)).fetchone()
            if prior_event:
                if prior_event != (fingerprint, job_id):
                    return Decision('HELD', None, None, 'Event identity reused with different binding')
                return Decision('DUPLICATE', job_id, action, 'Existing plan retained; no execution')
            prior_job = db.execute('SELECT binding FROM jobs WHERE job_id=?', (job_id,)).fetchone()
            if prior_job:
                require(prior_job == (encoded,))
                # Do not grow an unbounded duplicate-event log. No event row is
                # added for aliases; event authentication remains host-owned.
                return Decision('DUPLICATE', job_id, action, 'Same source revision and mission already planned')
            count = db.execute('SELECT count(*) FROM jobs').fetchone()[0]
            if count >= enrollment.max_jobs:
                return Decision('HELD', None, None, 'Queue job budget exhausted')
            db.execute('INSERT INTO jobs VALUES (?,?)', (job_id, encoded))
            db.execute('INSERT INTO events VALUES (?,?,?)', (event.event_id, fingerprint, job_id))
            return Decision('PLANNED', job_id, action, 'Observer plan persisted; live execution disabled')
