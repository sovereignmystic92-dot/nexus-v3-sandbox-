"""Single-worker, synthetic-only SQLite coordinator; no external adapters."""

import hashlib
import json
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3
from uuid import NAMESPACE_URL, uuid4, uuid5

from .authority import default_records, resolve
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

    def __init__(self, database, fixtures, *, authority_records=None,
                 runtime_identity="synthetic:runtime:local-harness", case_id="LOCAL-TRANSACTION"):
        self.database = Path(database).resolve()
        self.authority = resolve(default_records() if authority_records is None else authority_records)
        self.runtime_identity = runtime_identity
        self.case_id = case_id
        source_dir = Path(__file__).parent
        self.code_revision = "sha256:" + digest("".join(
            p.name + p.read_text() for p in sorted(source_dir.iterdir())
            if p.suffix in (".py", ".sql", ".json")))
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
            if "authority_revision" not in columns:
                raise ValueError("Old draft database; use a new disposable database")
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='endpoint_references'").fetchone():
                raise ValueError("Legacy database lacks reciprocal registration; retain it and use a new disposable database")

    def _connect(self):
        db = sqlite3.connect(self.database, isolation_level=None, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @staticmethod
    def _checkpoint(row):
        return Checkpoint(row["transaction_id"], row["state"], row["version"],
                          row["disposition"], row["next_action"])

    def _event(self, db, row, prior, evidence, started, receipt=None, operation_outcome=None):
        tid = row["transaction_id"]
        attempt = "synthetic:attempt:" + str(uuid4())
        artifacts = db.execute("SELECT artifact_id,payload_sha256 FROM artifacts WHERE transaction_id=? ORDER BY kind", (tid,)).fetchall()
        fixture = self.fixtures[(row["source_id"], row["source_revision"])]
        disposition = row["disposition"]
        verdict = ("VERIFIED" if disposition == "VERIFIED" else
                   "BLOCKED" if disposition == "BLOCKED" else
                   "FAILED" if disposition == "INCOMPLETE" else "PARTIALLY_VERIFIED")
        envelope = {
            "schema_version": 1, "run_id": tid + ":run", "case_id": self.case_id,
            "attempt_id": attempt, "transaction_id": tid,
            "fixture_revision": "sha256:" + digest(json.dumps(fixture, sort_keys=True)),
            "code_revision": self.code_revision, "runtime_identity": self.runtime_identity,
            "started_at_utc": started, "ended_at_utc": datetime.now(timezone.utc).isoformat(),
            "expected_result": "advance one checkpoint only when source and current authority permit; verify exact committed artifacts",
            "observed_result": evidence,
            "operation_outcome": operation_outcome or ("NOT_ATTEMPTED" if disposition == "BLOCKED" else "FAILED" if disposition == "INCOMPLETE" else "SUCCEEDED"),
            "protocol_verdict": verdict, "last_confirmed_state": row["state"],
            "next_action": row["next_action"], "artifact_ids": [a[0] for a in artifacts],
            "expected_hashes": {tid + ":" + kind: row["payload_sha256"] for kind in ("archive", "output", "registry")},
            "readback_hashes": receipt["readback_hashes"] if receipt else {},
            "reciprocal_readback": receipt.get("reciprocal_readback") if receipt else None,
            "reader_identity": receipt["reader_identity"] if receipt else None,
            "evidence_refs": [attempt],
            "authority_revision": self.authority.governing_revision,
            "bound_authority_revision": row["authority_revision"],
            "authority_provenance": list(self.authority.provenance),
            "readback_observed_at_utc": receipt["observed_at_utc"] if receipt else None,
            "limitations": ["local SQLite protocol only; not production readiness",
                            "operator-asserted synthetic data, runtime identity and authority roles",
                            "host isolation and independent human review unverified",
                            "immediate readback only; no leases or cryptographic event protection"],
        }
        db.execute("INSERT INTO attempts VALUES(?,?,?)", (attempt, tid, json.dumps(envelope, sort_keys=True)))
        db.execute("INSERT INTO events(transaction_id,prior_state,new_state,recorded_at_utc,evidence_ref) VALUES(?,?,?,?,?)",
                   (tid, prior, row["state"], envelope["ended_at_utc"], attempt))

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
        started = datetime.now(timezone.utc).isoformat()
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
                disposition = "OPEN" if complete and self.authority.allowed else "BLOCKED"
                action = ("validate source" if disposition == "OPEN" else
                          "resolve authority; submit under a new key" if not self.authority.allowed else
                          "supply a complete source under a new revision and key")
                db.execute("INSERT INTO transactions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                           (tid, request.idempotency_key, *binding[:4], int(request.source_complete),
                            self.authority.governing_revision,
                            "NEW", disposition, 0, action))
                row = db.execute("SELECT * FROM transactions WHERE transaction_id=?", (tid,)).fetchone()
                self._event(db, row, None, "synthetic fixture binding recorded; " + disposition + "; " + self.authority.reason, started)
                db.commit()
                return self._checkpoint(row)
            except BaseException:
                db.rollback()
                raise

    def _verify(self, row, payload):
        receipt = {"matched": True, "readback_hashes": {},
                   "reader_identity": "synthetic:reader:" + str(uuid4()),
                   "observed_at_utc": datetime.now(timezone.utc).isoformat()}
        # Fresh connection observes committed storage, never the writer's response.
        with closing(self._connect()) as reader:
            reader.execute("BEGIN")
            for kind in ("archive", "output", "registry"):
                artifact = reader.execute("SELECT * FROM artifacts WHERE transaction_id=? AND kind=?",
                                          (row["transaction_id"], kind)).fetchone()
                if not artifact:
                    receipt["matched"] = False
                    continue
                receipt["readback_hashes"][artifact["artifact_id"]] = digest(artifact["payload"])
                expected_id = row["transaction_id"] + ":" + kind
                destination = "synthetic:archive" if kind == "archive" else row["destination_id"]
                if (artifact["artifact_id"] != expected_id
                        or artifact["destination_id"] != destination
                        or artifact["payload"] != payload
                        or artifact["payload_sha256"] != row["payload_sha256"]
                        or digest(artifact["payload"]) != row["payload_sha256"]):
                    receipt["matched"] = False
            if not self._reciprocity_matches(reader, row["transaction_id"]):
                receipt["matched"] = False
            connection = reader.execute("SELECT * FROM connections WHERE transaction_id=?", (row["transaction_id"],)).fetchone()
            receipt["reciprocal_readback"] = {
                "connection": dict(connection) if connection is not None else None,
                "endpoint_references": [dict(ref) for ref in reader.execute(
                    "SELECT * FROM endpoint_references WHERE connection_id=? ORDER BY endpoint_type",
                    (row["transaction_id"] + ":connection",))],
            }
            return receipt

    @staticmethod
    def _connection_binding(tid):
        return (tid + ":connection", tid, "derived_from", tid + ":archive", tid + ":output")

    @staticmethod
    def _endpoint_binding(tid):
        return [(tid + ":connection", tid + ":archive", "source_archive"),
                (tid + ":connection", tid + ":output", "derived_output")]

    def _reciprocity_matches(self, reader, tid):
        connection = reader.execute("SELECT * FROM connections WHERE transaction_id=?", (tid,)).fetchone()
        if (connection is None or tuple(connection)[:5] != self._connection_binding(tid)
                or type(connection["version"]) is not int or connection["version"] < 1):
            return False
        refs = reader.execute("SELECT * FROM endpoint_references WHERE connection_id=? ORDER BY endpoint_type",
                              (tid + ":connection",)).fetchall()
        if sorted(tuple(r) for r in refs) != sorted(self._endpoint_binding(tid)):
            return False
        for aid, kind, destination in ((tid + ":archive", "archive", "synthetic:archive"),
                                       (tid + ":output", "output", "synthetic:output")):
            endpoint = reader.execute("SELECT transaction_id,kind,destination_id FROM artifacts WHERE artifact_id=?", (aid,)).fetchone()
            if endpoint is None or tuple(endpoint) != (tid, kind, destination):
                return False
        return True

    def repair_reciprocity(self, transaction_id, expected_version):
        """Explicit bounded repair of missing references only; never replace conflicts.

        Only a REGISTERED incomplete transaction is eligible. Repair commits before
        independent verification through resume. A repeat is a complete no-op.
        """
        tid = transaction_id
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute("SELECT * FROM transactions WHERE transaction_id=?", (tid,)).fetchone()
                if row is None:
                    raise KeyError(tid)
                if row["version"] != expected_version:
                    raise StaleCheckpoint("Read the current checkpoint before repair")
                if not self.authority.allowed or row["authority_revision"] != self.authority.governing_revision:
                    raise BindingConflict("Authority does not permit repair")
                if self._reciprocity_matches(db, tid):
                    db.commit()
                    return self._checkpoint(row)
                if row["state"] != "REGISTERED" or row["disposition"] != "INCOMPLETE":
                    raise BindingConflict("Repair requires a held REGISTERED checkpoint")
                conn = db.execute("SELECT * FROM connections WHERE transaction_id=?", (tid,)).fetchone()
                if conn is None or tuple(conn)[:5] != self._connection_binding(tid):
                    raise BindingConflict("Missing or changed connection; preserve for investigation")
                fixture = self._fixture(Request(row["idempotency_key"], row["source_id"], row["source_revision"],
                                                row["destination_id"], row["payload_sha256"], bool(row["source_complete"])))
                if not fixture["source_complete"] or not row["source_complete"]:
                    raise BindingConflict("Incomplete source; no repair")
                for aid, kind, dest in ((tid + ":archive", "archive", "synthetic:archive"),
                                         (tid + ":output", "output", "synthetic:output")):
                    art = db.execute("SELECT * FROM artifacts WHERE artifact_id=?", (aid,)).fetchone()
                    expected = (aid, tid, kind, dest, fixture["payload"], row["payload_sha256"])
                    if art is None or tuple(art) != expected:
                        raise BindingConflict("Endpoint identity/type/payload conflict; no repair")
                expected_refs = self._endpoint_binding(tid)
                existing = db.execute("SELECT * FROM endpoint_references WHERE connection_id=?", (conn[0],)).fetchall()
                if any(tuple(ref) not in expected_refs for ref in existing):
                    raise BindingConflict("Conflicting reciprocal reference; no repair")
                for ref in expected_refs:
                    db.execute("INSERT OR IGNORE INTO endpoint_references VALUES(?,?,?)", ref)
                db.execute("UPDATE connections SET version=version+1 WHERE connection_id=?", (conn[0],))
                db.execute("UPDATE transactions SET version=version+1 WHERE transaction_id=?", (tid,))
                updated = db.execute("SELECT * FROM transactions WHERE transaction_id=?", (tid,)).fetchone()
                self._event(db, updated, row["state"], "bounded reciprocal repair committed; independent verification pending",
                            datetime.now(timezone.utc).isoformat(), operation_outcome="SUCCEEDED")
                db.commit()
                return self._checkpoint(updated)
            except BaseException:
                db.rollback()
                raise

    def resume(self, transaction_id: str, expected_version: int) -> Checkpoint:
        started = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute("SELECT * FROM transactions WHERE transaction_id=?", (transaction_id,)).fetchone()
                if row is None:
                    raise KeyError(transaction_id)
                if row["version"] != expected_version:
                    raise StaleCheckpoint("Read the current checkpoint before resuming")
                if (row["disposition"] == "VERIFIED" or
                        (row["disposition"] == "BLOCKED" and not row["next_action"].startswith("restore bound"))):
                    db.commit()
                    return self._checkpoint(row)
                request = Request(row["idempotency_key"], row["source_id"], row["source_revision"],
                                  row["destination_id"], row["payload_sha256"], bool(row["source_complete"]))
                fixture = self._fixture(request)
                state = row["state"]
                disposition = "OPEN"
                receipt = None
                evidence = "local checkpoint committed"
                if not self.authority.allowed or row["authority_revision"] != self.authority.governing_revision:
                    new, disposition, action = state, "BLOCKED", "restore bound current authority or submit under a new key"
                    evidence = "authority hold: " + self.authority.reason + "; governing revision checked"
                elif not fixture["source_complete"]:
                    new, disposition, action = state, "BLOCKED", "supply complete source under a new revision and key"
                elif state == "REGISTERED":
                    receipt = self._verify(row, fixture["payload"])
                    matches = receipt["matched"]
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
                        if kind == "registry" and disposition == "OPEN":
                            binding = self._connection_binding(transaction_id)
                            connection = db.execute("SELECT * FROM connections WHERE transaction_id=?", (transaction_id,)).fetchone()
                            if connection is not None and tuple(connection)[:5] != binding:
                                raise BindingConflict("Existing typed connection conflicts; preserve it")
                            if connection is None:
                                db.execute("INSERT INTO connections VALUES(?,?,?,?,?,1)", binding)
                                for ref in self._endpoint_binding(transaction_id):
                                    db.execute("INSERT INTO endpoint_references VALUES(?,?,?)", ref)
                updated = db.execute("UPDATE transactions SET state=?,disposition=?,version=version+1,next_action=? WHERE transaction_id=? AND version=?",
                                     (new, disposition, action, transaction_id, expected_version))
                if updated.rowcount != 1:
                    raise StaleCheckpoint("Checkpoint changed")
                result = db.execute("SELECT * FROM transactions WHERE transaction_id=?", (transaction_id,)).fetchone()
                self._event(db, result, state, evidence, started, receipt)
                db.commit()
                return self._checkpoint(result)
            except BaseException:
                db.rollback()
                raise

