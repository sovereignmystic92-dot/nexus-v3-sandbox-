"""Durable, local-only paper trade intent ledger. No brokerage calls.

States: PREPARED -> RESERVED -> UNCERTAIN -> RECONCILED.
An UNCERTAIN order must be independently reconciled, never blindly retried.
"""
import json
import sqlite3
from pathlib import Path

class JournalConflict(RuntimeError):
    pass

class PaperJournal:
    def __init__(self, db_path):
        self.db_path = str(Path(db_path))
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS trade_intents (
                client_order_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN
                  ('PREPARED','RESERVED','UNCERTAIN','RECONCILED','REJECTED')),
                broker_order_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS trade_events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                client_order_id TEXT NOT NULL,
                event TEXT NOT NULL,
                detail TEXT NOT NULL,
                at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(client_order_id) REFERENCES trade_intents(client_order_id)
            )""")

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        return db

    def prepare(self, client_order_id, payload):
        if not isinstance(client_order_id, str) or not client_order_id.strip():
            raise JournalConflict("client order ID required")
        if not isinstance(payload, dict) or not payload:
            raise JournalConflict("nonempty intent payload required")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT payload_json FROM trade_intents WHERE client_order_id=?",
                (client_order_id,)).fetchone()
            if existing:
                if existing[0] != encoded:
                    raise JournalConflict("client order ID reused with different intent")
                return False
            db.execute("INSERT INTO trade_intents(client_order_id,payload_json,state) VALUES(?,?,'PREPARED')",
                       (client_order_id, encoded))
            db.execute("INSERT INTO trade_events(client_order_id,event,detail) VALUES(?, 'PREPARED', '')",
                       (client_order_id,))
            return True

    def transition(self, client_order_id, expected, target, detail="", broker_order_id=None):
        allowed = {("PREPARED", "RESERVED"), ("RESERVED", "UNCERTAIN"),
                   ("UNCERTAIN", "RECONCILED"), ("PREPARED", "REJECTED")}
        if (expected, target) not in allowed:
            raise JournalConflict("invalid state transition")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            result = db.execute("""UPDATE trade_intents SET state=?,broker_order_id=?,
                       updated_at=CURRENT_TIMESTAMP
                       WHERE client_order_id=? AND state=?""",
                       (target, broker_order_id, client_order_id, expected))
            if result.rowcount != 1:
                raise JournalConflict("state changed, missing, or duplicate transition")
            db.execute("INSERT INTO trade_events(client_order_id,event,detail) VALUES(?,?,?)",
                       (client_order_id, target, detail))

    def state(self, client_order_id):
        with self._connect() as db:
            row = db.execute("SELECT state FROM trade_intents WHERE client_order_id=?",
                             (client_order_id,)).fetchone()
            return row[0] if row else None

    def unresolved(self):
        with self._connect() as db:
            return db.execute("""SELECT client_order_id,state FROM trade_intents
                WHERE state IN ('RESERVED','UNCERTAIN') ORDER BY client_order_id""").fetchall()
