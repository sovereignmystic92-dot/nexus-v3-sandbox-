"""Fail-closed durable provider-custody observations for the ChatGPT adapter.

No connector call, no authentication, no permission granting or live writes.
The independent host must supply trusted verified evidence, not chat text.
A persisted DISPATCHING intent is never automatically replayed.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sqlite3

HEX = re.compile(r"^[a-f0-9]{64}$")
ID = re.compile(r"^[a-zA-Z0-9:_./-]{1,256}$")
INTENT_FIELDS = frozenset({"transaction_id", "notion_source_id",
    "notion_revision", "notion_sha256", "cortex_output_id",
    "cortex_revision", "cortex_sha256", "policy_revision"})
PROOF_FIELDS = frozenset({"transaction_id", "intent_sha256",
    "notion_source_id", "notion_revision", "notion_sha256",
    "cortex_output_id", "cortex_revision", "cortex_sha256",
    "notion_complete", "cortex_complete", "authority_verified",
    "independent_readback"})


@dataclass(frozen=True)
class CustodyResult:
    status: str
    next_action: str
    transaction_id: str | None = None
    automatic_execution: bool = False
    provider_writes: int = 0
    cp09: str = "NOT_PROVEN"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
        separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def valid_intent(i):
    return (type(i) is dict and set(i) == INTENT_FIELDS
            and all(type(v) is str and bool(v) and ID.fullmatch(v)
                    for k, v in i.items() if not k.endswith("sha256"))
            and all(type(i[k]) is str and HEX.fullmatch(i[k])
                    for k in ("notion_sha256", "cortex_sha256")))


class CustodyLedger:
    """Single-host durable SQLite ledger. NOT remotely fenced (CP09 open)."""

    def __init__(self, path, *, initialize=False):
        self.path = Path(path)
        if self.path.is_symlink():
            raise ValueError("Symlink ledger forbidden")
        if initialize:
            with self.path.open("xb"):
                pass
        if not self.path.is_file():
            raise ValueError("Missing ledger; no silent resets")
        with self.connect() as db:
            if initialize:
                db.execute("CREATE TABLE entries (id TEXT PRIMARY KEY, intent_hash TEXT NOT NULL,"
                           " intent_json TEXT NOT NULL, state TEXT NOT NULL,"
                           " proof_hash TEXT)")
            elif "entries" not in {r[0] for r in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}:
                raise ValueError("Invalid ledger")

    def connect(self):
        return sqlite3.connect(self.path.resolve().as_uri() + "?mode=rw", uri=True)

    def prepare(self, intent):
        if not valid_intent(intent):
            return CustodyResult("HELD", "INVALID_INTENT")
        identifier = intent["transaction_id"]
        encoded = json.dumps(intent, sort_keys=True, separators=(",", ":"))
        fingerprint = digest(intent)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT intent_hash,state FROM entries WHERE id=?",
                             (identifier,)).fetchone()
            if row:
                if row[0] != fingerprint:
                    return CustodyResult("HELD", "CONFLICTING_INTENT_NO_RETRY",identifier)
                return CustodyResult(row[1], "NO_REPLAY_OR_DUPLICATE_WRITE",identifier)
            db.execute("INSERT INTO entries VALUES (?,?,?,?,NULL)",
                       (identifier, fingerprint, encoded, "PREPARED"))
        return CustodyResult("PREPARED", "REQUIRES_TRUSTED_HOST_PREWRITE_CHECK",identifier)

    def mark_dispatching(self, transaction_id):
        """Record uncertainty BEFORE any outside write. Never dispatch itself."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state FROM entries WHERE id=?",
                             (transaction_id,)).fetchone()
            if not row or row[0] != "PREPARED":
                return CustodyResult("HELD", "RECONCILE_NO_REPLAY",transaction_id)
            db.execute("UPDATE entries SET state='DISPATCHING' WHERE id=?",
                       (transaction_id,))
        return CustodyResult("DISPATCHING","HOLD_FOR_INDEPENDENT_READBACK",transaction_id)

    def reconcile(self, proof):
        if type(proof) is not dict or set(proof) != PROOF_FIELDS:
            return CustodyResult("HELD", "INVALID_PROOF")
        if any(type(proof[k]) is not bool for k in (
                "notion_complete","cortex_complete","authority_verified",
                "independent_readback")):
            return CustodyResult("HELD", "INVALID_PROOF_FLAGS")
        tid = proof["transaction_id"]
        if type(tid) is not str or not ID.fullmatch(tid):
            return CustodyResult("HELD","INVALID_TRANSACTION_ID")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT intent_json,intent_hash,state,proof_hash "
                             "FROM entries WHERE id=?", (tid,)).fetchone()
            if not row or row[2] != "DISPATCHING":
                return CustodyResult("HELD","RECONCILE_NO_REPLAY",tid)
            intent, ihash = json.loads(row[0]),row[1]
            pairs = (("notion_source_id","notion_source_id"),
                     ("notion_revision","notion_revision"),
                     ("notion_sha256","notion_sha256"),
                     ("cortex_output_id","cortex_output_id"),
                     ("cortex_revision","cortex_revision"),
                     ("cortex_sha256","cortex_sha256"))
            if (proof["intent_sha256"] != ihash or
                    any(proof[k] != intent[v] for k,v in pairs)):
                return CustodyResult("HELD","RECONCILE_MISMATCH_NO_RETRY",tid)
            if not all(proof[k] for k in ("notion_complete","cortex_complete",
                                         "authority_verified","independent_readback")):
                return CustodyResult("HELD","INCOMPLETE_OR_UNTRUSTED_PROOF",tid)
            db.execute("UPDATE entries SET state='READBACK_MATCHED',proof_hash=? "
                       "WHERE id=?", (digest(proof),tid))
        return CustodyResult("READBACK_MATCHED",
                             "REVIEW_HOST_ATTESTATION_AND_COMPLETION_GATES",tid)
