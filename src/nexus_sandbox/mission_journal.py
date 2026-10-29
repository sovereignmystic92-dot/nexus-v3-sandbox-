"""Local SQLite custody for non-executing mission dispatch decisions.

No scheduler, service, network, Cortex/Notion callback, or external write.
Operator explicitly provisions a private file. No recovery path recreates it.
Evidence is caller-supplied and not independently authenticated by this module.
"""
from contextlib import closing
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat

from .mission_dispatcher import Mission, dispatch


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _hash(prev, entry):
    return hashlib.sha256((prev + "\n" + _canonical(entry)).encode()).hexdigest()


def _path(path, *, existing):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("Absolute non-symlink journal path required")
    parent = path.parent
    folder = parent.lstat()
    if not stat.S_ISDIR(folder.st_mode) or folder.st_mode & 0o077 or folder.st_uid != os.getuid():
        raise ValueError("Private owned journal directory required")
    if existing:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_nlink != 1 or info.st_uid != os.getuid():
            raise ValueError("Private owned journal file required")
    return path


def _evidence(trigger=(), dependencies=(), verified=(), blocked=(), active=False):
    for values in (trigger, dependencies, verified, blocked):
        if type(values) not in (tuple, frozenset):
            raise ValueError("Evidence must be immutable")
    if type(active) is not bool:
        raise ValueError("Authorization flag must be boolean")
    return dict(
        trigger=tuple(sorted(trigger)),
        dependencies=tuple(sorted(dependencies)),
        verified=tuple(sorted(verified)),
        blocked=tuple(sorted(blocked)),
        active=active,
    )


class MissionJournal:
    @classmethod
    def provision(cls, path, identity):
        if type(identity) is not str or not identity:
            raise ValueError("Explicit identity required")
        path = _path(path, existing=False)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        try:
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("PRAGMA synchronous=FULL")
                db.execute("CREATE TABLE journal_identity(identity TEXT NOT NULL)")
                db.execute("INSERT INTO journal_identity VALUES (?)", (identity,))
                db.execute("CREATE TABLE mission_events(mission_id TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL, prev_hash TEXT NOT NULL, entry_hash TEXT NOT NULL, PRIMARY KEY(mission_id, revision))")
        except Exception:
            # Leave any partial provisioned file for inspection; never silently replace it.
            raise
        return cls(path, identity)

    def __init__(self, path, identity):
        if type(identity) is not str or not identity:
            raise ValueError("Explicit identity required")
        self.path = _path(path, existing=True)
        self.identity = identity
        with self._connect() as db:
            self._validate(db)

    def _connect(self):
        _path(self.path, existing=True)
        db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=1)
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA busy_timeout=1000")
        return db

    def _validate(self, db):
        if db.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise ValueError("Journal integrity failure")
        if db.execute("SELECT identity FROM journal_identity").fetchall() != [(self.identity,)]:
            raise ValueError("Journal identity mismatch")

    def _history(self, db, mission_id):
        rows = db.execute(
            "SELECT revision,payload,prev_hash,entry_hash FROM mission_events WHERE mission_id=? ORDER BY revision",
            (mission_id,),
        ).fetchall()
        prev = "GENESIS"
        for index, (revision, payload, stored_prev, digest) in enumerate(rows, 1):
            if revision != index or stored_prev != prev:
                raise ValueError("Journal history gap or conflict")
            item = json.loads(payload)
            if item.get("mission_id") != mission_id or _canonical(item) != payload or _hash(prev, item) != digest:
                raise ValueError("Journal entry tampering")
            prev = digest
        return rows

    def observe(self, mission_id):
        if type(mission_id) is not str or not mission_id:
            raise ValueError("Explicit mission required")
        with closing(self._connect()) as db:
            self._validate(db)
            rows = self._history(db, mission_id)
            return json.loads(rows[-1][1]) if rows else None

    def record(self, mission, *, observed_triggers=(), satisfied_dependencies=(),
               verified_steps=(), blocked_steps=(), authorized_active=False,
               expected_revision=0):
        if type(mission) is not Mission:
            raise ValueError("Explicit mission contract required")
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError("Expected revision required")
        evidence = _evidence(observed_triggers, satisfied_dependencies,
                             verified_steps, blocked_steps, authorized_active)
        decision = dispatch(mission, observed_triggers=observed_triggers,
                            satisfied_dependencies=satisfied_dependencies,
                            verified_steps=verified_steps,
                            blocked_steps=blocked_steps,
                            authorized_active=authorized_active)
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            self._validate(db)
            rows = self._history(db, mission.mission_id)
            revision = len(rows)
            previous = json.loads(rows[-1][1]) if rows else None
            if previous and previous["decision"]["contract_digest"] != decision["contract_digest"]:
                raise ValueError("Mission contract changed; use a new mission identity")
            if previous and previous["evidence"] == evidence and previous["decision"] == decision:
                db.commit()
                return previous
            if expected_revision != revision:
                raise ValueError("Stale journal revision")
            if previous:
                old = previous["evidence"]
                # Never silently retract observed evidence or release an unresolved hold.
                for field in ("trigger", "dependencies", "verified", "blocked"):
                    if not set(old[field]).issubset(evidence[field]):
                        raise ValueError("Evidence retraction requires separate reconciliation")
                if old["active"] and not evidence["active"]:
                    raise ValueError("Active authorization change requires new bounded mission")
                if previous["decision"]["state"] == "COMPLETE":
                    raise ValueError("Completed mission cannot be reopened")
            item = dict(mission_id=mission.mission_id, revision=revision + 1,
                        contract=asdict(mission), evidence=evidence, decision=decision)
            prior_hash = rows[-1][3] if rows else "GENESIS"
            payload = _canonical(item)
            db.execute("INSERT INTO mission_events VALUES (?,?,?,?,?)",
                       (mission.mission_id, revision + 1, payload, prior_hash, _hash(prior_hash, item)))
            db.commit()
        saved = self.observe(mission.mission_id)
        if saved != item:
            raise ValueError("Independent local journal readback mismatch")
        return saved
