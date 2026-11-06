"""Durable, fail-closed intent journal for host-mediated Cortex handoffs.

The host must supply an exclusive process lock and independently authenticated
callbacks. No remote operations, scheduling, or production permission here.
"""
from contextlib import closing
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import sqlite3


class JournalHold(RuntimeError):
    pass


@dataclass(frozen=True)
class Intent:
    transaction_key: str
    source_url: str
    analysis_url: str
    source_revision: str
    analysis_revision: str
    destination_account: str
    destination_owner: str
    analysis_digest: str


def analysis_hash(text):
    if not isinstance(text, str) or not text.strip():
        raise JournalHold("missing derived analysis")
    return sha256(text.encode("utf-8")).hexdigest()


class HandoffJournal:
    def __init__(self, path: Path):
        self.path = Path(path)
        if not self.path.parent.is_dir():
            raise JournalHold("journal parent must exist")
        with closing(self._connect()) as db:
            with db:
                db.execute("""CREATE TABLE IF NOT EXISTS handoff_intents (
                    transaction_key TEXT PRIMARY KEY,
                    binding TEXT NOT NULL,
                    state TEXT NOT NULL,
                    module_id TEXT)""")
                db.execute("""CREATE TABLE IF NOT EXISTS handoff_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_key TEXT NOT NULL,
                    state TEXT NOT NULL,
                    module_id TEXT)""")

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA busy_timeout=5000")
        return db

    def begin(self, intent: Intent):
        if not isinstance(intent, Intent) or any(
            not isinstance(v, str) or not v.strip() for v in vars(intent).values()
        ):
            raise JournalHold("complete immutable binding required")
        binding = json.dumps(vars(intent), sort_keys=True)
        with closing(self._connect()) as db, db:
            old = db.execute("SELECT binding,state,module_id FROM handoff_intents WHERE transaction_key=?",
                             (intent.transaction_key,)).fetchone()
            if old:
                if old[0] != binding:
                    raise JournalHold("transaction key reused with different binding")
                return old[1], old[2]
            db.execute("INSERT INTO handoff_intents VALUES (?,?,?,NULL)",
                       (intent.transaction_key, binding, "PREPARED"))
            db.execute("INSERT INTO handoff_events(transaction_key,state) VALUES (?,?)",
                       (intent.transaction_key, "PREPARED"))
        return "PREPARED", None

    def mark_write_intent(self, intent: Intent):
        """Persist write intent before the host invokes a create callback.

        Once marked, all retries must reconcile remotely; never create again
        merely because no receipt was recorded.
        """
        binding = json.dumps(vars(intent), sort_keys=True)
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT binding,state FROM handoff_intents WHERE transaction_key=?",
                             (intent.transaction_key,)).fetchone()
            if row is None or row[0] != binding or row[1] != "PREPARED":
                raise JournalHold("write intent cannot be issued or repeated")
            db.execute("UPDATE handoff_intents SET state='WRITE_INTENT' WHERE transaction_key=?",
                       (intent.transaction_key,))
            db.execute("INSERT INTO handoff_events(transaction_key,state) VALUES (?,?)",
                       (intent.transaction_key, "WRITE_INTENT"))

    def reconcile_verified(self, intent: Intent, module_id: str):
        if not isinstance(module_id, str) or not module_id.strip():
            raise JournalHold("independently verified module ID required")
        binding = json.dumps(vars(intent), sort_keys=True)
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT binding,state,module_id FROM handoff_intents WHERE transaction_key=?",
                             (intent.transaction_key,)).fetchone()
            if row is None or row[0] != binding or row[1] not in ("WRITE_INTENT", "VERIFIED"):
                raise JournalHold("no matching write intent")
            if row[2] is not None and row[2] != module_id:
                raise JournalHold("verified module identity changed")
            db.execute("UPDATE handoff_intents SET state='VERIFIED',module_id=? WHERE transaction_key=?",
                       (module_id, intent.transaction_key))
            db.execute("INSERT INTO handoff_events(transaction_key,state,module_id) VALUES (?,?,?)",
                       (intent.transaction_key, "VERIFIED", module_id))
