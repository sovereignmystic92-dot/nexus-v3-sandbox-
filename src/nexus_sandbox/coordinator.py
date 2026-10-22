"""Single-worker, synthetic-only SQLite coordinator; no external adapters."""

import hashlib
import json
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3
from uuid import NAMESPACE_URL, uuid5

from .contracts import Checkpoint, Request


class BindingConflict(ValueError):
    pass


class StaleCheckpoint(ValueError):
    pass


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SQLiteCoordinator:
    """Explicit local DB path and fixture catalog. Not a host security boundary.

    submit returns a durable checkpoint; each resume advances at most one state.
    Reopening an existing DB never reapplies the schema. No automatic migrations.
    """

    def __init__(self, database, fixtures):
        self.database = Path(database).resolve()
        self.fixtures = {}
        for fixture in fixtures:
            f = json.loads(json.dumps(fixture))
            key = (f["source_id"], f["source_revision"])
            if (f.get("synthetic") is not True
                    or not re.fullmatch(r"synthetic:source:[A-Za-z0-9_-]+", key[0])
                    or f.get("destination_id") != "synthetic:output"
                    or type(f.get("source_complete")) is not bool
                    or not isinstance(f.get("payload"), str)
                    or key in self.fixtures):
                raise ValueError("Invalid or duplicate synthetic fixture")
            self.fixtures[key] = f
        with closing(self._connect()) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='transactions'").fetchone():
                db.executescript(Path(__file__).with_name("schema.sql").read_text())
            columns = {r[1] for r in db.execute("PRAGMA table_info(transactions)")}
            if "source_complete" not in columns:
                raise ValueError("Old draft database; use a new disposable database")

    def _connect(self):
        db = sqlite3.connect(self.database, isolation_level=None, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @staticmethod
    def _checkpoint(row):
        return Checkpoint(row["transaction_id"], row["state"], row["version"],
                          row["disposition"], row["next_action"])

    @staticmethod
    def _event(db, tid, prior, state, evidence):
        db.execute("INSERT INTO events(transaction_id,prior_state,new_state,recorded_at_utc,evidence_ref) VALUES(?,?,?,?,?)",
                   (tid, prior, state, datetime.now(timezone.utc).isoformat(), evidence))

    def _fixture(self, request):
        if (request.destination_id != "synthetic:output"
                or not isinstance(request.idempotency_key, str)
                or not re.fullmatch(r"synthetic:request:[A-Za-z0-9_-]+", request.idempotency_key)
                or type(request.source_complete) is not bool):
            raise ValueError("Request outside synthetic scope")
        fixture = self.fixtures.get((request.source_id, request.source_revision))
        if fixture is None or digest(fixture["payload"]) != request.payload_sha256:
            raise ValueError("Source revision or payload hash does not match fixture")
        return fixture

    def submit(self, request: Request) -> Checkpoint:
        # Reject changed binding before consulting possibly changed fixture catalogs.
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                existing = db.execute("SELECT * FROM transactions WHERE idempotency_key=?", (request.idempotency_key,)).fetchone()
                binding = (request.source_id, request.source_revision, request.destination_id,
                           request.payload_sha256, request.source_complete)
                if existing:
                    old = tuple(existing[k] for k in ("source_id", "source_revision", "destination_id", "payload_sha256", "source_complete"))
                    if old != binding:
                        raise BindingConflict("Idempotency key is bound to a different request")
                    self._fixture(request)
                    db.commit()
                    return self._checkpoint(existing)
                fixture = self._fixture(request)
                complete = request.source_complete and fixture["source_complete"]
                tid = "synthetic:transaction:" + str(uuid5(NAMESPACE_URL, request.idempotency_key))
                disposition = "OPEN" if complete else "BLOCKED"
                action = "validate source" if complete else "supply a complete source under a new revision and key"
                db.execute("INSERT INTO transactions VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           (tid, request.idempotency_key, *binding[:4], int(request.source_complete),
                            "NEW", disposition, 0, action))
                self._event(db, tid, None, "NEW", "synthetic fixture binding recorded; " + disposition)
                row = db.execute("SELECT * FROM transactions WHERE transaction_id=?", (tid,)).fetchone()
                db.commit()
                return self._checkpoint(row)
            except BaseException:
                db.rollback()
                raise

    def _verify(self, row, payload):
        # Fresh connection observes committed storage, never the writer's response.
        with closing(self._connect()) as reader:
            reader.execute("BEGIN")
            for kind in ("archive", "output", "registry"):
                artifact = reader.execute("SELECT * FROM artifacts WHERE transaction_id=? AND kind=?",
                                          (row["transaction_id"], kind)).fetchone()
                if not artifact:
                    return False
                expected_id = row["transaction_id"] + ":" + kind
                destination = "synthetic:archive" if kind == "archive" else row["destination_id"]
                if (artifact["artifact_id"] != expected_id
                        or artifact["destination_id"] != destination
                        or artifact["payload"] != payload
                        or artifact["payload_sha256"] != row["payload_sha256"]
                        or digest(artifact["payload"]) != row["payload_sha256"]):
                    return False
            return True

    def resume(self, transaction_id: str, expected_version: int) -> Checkpoint:
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute("SELECT * FROM transactions WHERE transaction_id=?", (transaction_id,)).fetchone()
                if row is None:
                    raise KeyError(transaction_id)
                if row["version"] != expected_version:
                    raise StaleCheckpoint("Read the current checkpoint before resuming")
                if row["disposition"] in ("BLOCKED", "VERIFIED"):
                    db.commit()
                    return self._checkpoint(row)
                request = Request(row["idempotency_key"], row["source_id"], row["source_revision"],
                                  row["destination_id"], row["payload_sha256"], bool(row["source_complete"]))
                fixture = self._fixture(request)
                state = row["state"]
                disposition = "OPEN"
                evidence = "local checkpoint committed"
                if not fixture["source_complete"]:
                    new, disposition, action = state, "BLOCKED", "supply complete source under a new revision and key"
                elif state == "REGISTERED":
                    matches = self._verify(row, fixture["payload"])
                    new = "VERIFIED" if matches else state
                    disposition = "VERIFIED" if matches else "INCOMPLETE"
                    action = "none" if matches else "inspect and repair existing artifacts; retry verification"
                    evidence = "fresh SQLite reader exact ID/destination/payload/hash match" if matches else "fresh SQLite reader mismatch; no verification claim"
                else:
                    progression = {"NEW": ("VALIDATED", None), "VALIDATED": ("ARCHIVED", "archive"),
                                   "ARCHIVED": ("OUTPUT_CREATED", "output"), "OUTPUT_CREATED": ("REGISTERED", "registry")}
                    new, kind = progression[state]
                    action = "resume from " + new
                    if kind:
                        aid = transaction_id + ":" + kind
                        destination = "synthetic:archive" if kind == "archive" else row["destination_id"]
                        old = db.execute("SELECT * FROM artifacts WHERE transaction_id=? AND kind=?", (transaction_id, kind)).fetchone()
                        expected = (aid, transaction_id, kind, destination, fixture["payload"], row["payload_sha256"])
                        if old and tuple(old) != expected:
                            new, disposition, action = state, "INCOMPLETE", "inspect and repair existing artifact; do not replace"
                            evidence = "existing artifact conflicts with expected binding"
                        elif not old:
                            db.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?)", expected)
                updated = db.execute("UPDATE transactions SET state=?,disposition=?,version=version+1,next_action=? WHERE transaction_id=? AND version=?",
                                     (new, disposition, action, transaction_id, expected_version))
                if updated.rowcount != 1:
                    raise StaleCheckpoint("Checkpoint changed")
                self._event(db, transaction_id, state, new, evidence)
                result = db.execute("SELECT * FROM transactions WHERE transaction_id=?", (transaction_id,)).fetchone()
                db.commit()
                return self._checkpoint(result)
            except BaseException:
                db.rollback()
                raise
