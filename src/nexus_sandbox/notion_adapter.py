"""Credential-free external persistence contract; no Notion SDK or network client.

One operator/worker only. A transport must supply complete, fresh observations.
An ambiguous create is never retried blindly, including after a process restart.
"""

from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Protocol


class BindingConflict(ValueError):
    pass


@dataclass(frozen=True)
class Binding:
    key: str
    parent_id: str
    title: str
    payload: str

    @property
    def payload_sha256(self):
        return hashlib.sha256(self.payload.encode()).hexdigest()


@dataclass(frozen=True)
class Page:
    page_id: str
    parent_id: str
    key: str
    title: str
    payload: str
    payload_sha256: str
    synthetic: bool
    complete: bool = True


@dataclass(frozen=True)
class Listing:
    pages: tuple[Page, ...]
    complete: bool


@dataclass(frozen=True)
class Receipt:
    status: str
    page_id: str | None
    reason: str


class Transport(Protocol):
    """No credentials in this interface. Implementations must not mutate on reads.

    find_direct_children must enumerate the bound root completely, including
    pagination and body-key inspection; title search alone is insufficient.
    Root attestation is an observation, not permission or credential isolation.
    """

    def sandbox_marker(self, parent_id: str) -> str: ...
    def find_direct_children(self, parent_id: str, key: str) -> Listing: ...
    def create_child(self, binding: Binding) -> str: ...
    def fetch_page(self, page_id: str) -> Page: ...


class NotionAdapter:
    def __init__(self, journal: Path, sandbox_parent: str, transport: Transport):
        if not re.fullmatch(r"[0-9a-f]{32}", sandbox_parent.replace("-", "")):
            raise ValueError("Explicit sandbox UUID required")
        self.parent = sandbox_parent
        self.transport = transport
        self.journal = Path(journal)
        with closing(self._db()) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS external_receipts (
                    key TEXT PRIMARY KEY, binding_json TEXT NOT NULL,
                    status TEXT NOT NULL, page_id TEXT, reason TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS external_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL, status TEXT NOT NULL, page_id TEXT,
                    reason TEXT NOT NULL, observed_at_utc TEXT NOT NULL);
            """)

    def _db(self):
        return sqlite3.connect(self.journal)

    def _save(self, binding, status, page_id, reason):
        encoded = json.dumps(asdict(binding), sort_keys=True)
        with closing(self._db()) as db, db:
            old = db.execute("SELECT binding_json FROM external_receipts WHERE key=?", (binding.key,)).fetchone()
            if old and old[0] != encoded:
                raise BindingConflict("Key already bound to different content or destination")
            db.execute("INSERT INTO external_receipts VALUES(?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET status=excluded.status,page_id=excluded.page_id,reason=excluded.reason",
                       (binding.key, encoded, status, page_id, reason))
            db.execute("INSERT INTO external_events(key,status,page_id,reason,observed_at_utc) VALUES(?,?,?,?,?)",
                       (binding.key, status, page_id, reason, datetime.now(timezone.utc).isoformat()))
        return Receipt(status, page_id, reason)

    def _readback(self, binding, page_id):
        try:
            page = self.transport.fetch_page(page_id)
        except Exception:
            return self._save(binding, "UNKNOWN", page_id, "Read unavailable; reconcile known ID before any create")
        expected = Page(page_id, binding.parent_id, binding.key, binding.title,
                        binding.payload, binding.payload_sha256, True)
        if (page != expected or type(page.synthetic) is not bool or type(page.complete) is not bool):
            return self._save(binding, "MISMATCH", page_id, "Fetched identity, parent, key, title, content or completeness mismatch; preserve page")
        return self._save(binding, "VERIFIED", page_id, "Transport read matched exact binding; freshness depends on transport")

    def ensure(self, binding: Binding) -> Receipt:
        if binding.parent_id != self.parent:
            raise ValueError("Destination outside explicit sandbox allowlist")
        if not re.fullmatch(r"synthetic:request:[A-Za-z0-9_-]+", binding.key):
            raise ValueError("Synthetic key required")
        if not binding.title or len(binding.payload.encode()) > 65536:
            raise ValueError("Bounded titled fixture required")
        encoded = json.dumps(asdict(binding), sort_keys=True)
        with closing(self._db()) as db:
            row = db.execute("SELECT binding_json,status,page_id FROM external_receipts WHERE key=?", (binding.key,)).fetchone()
        if row and row[0] != encoded:
            raise BindingConflict("Key already bound to different content or destination")
        try:
            if self.transport.sandbox_marker(self.parent) != "synthetic:notion:sandbox:v1":
                return self._save(binding, "BLOCKED", row[2] if row else None, "Sandbox marker not confirmed")
        except Exception:
            return self._save(binding, "BLOCKED", row[2] if row else None, "Sandbox root observation unavailable")
        if row and row[2]:
            return self._readback(binding, row[2])
        try:
            listing = self.transport.find_direct_children(self.parent, binding.key)
        except Exception:
            return self._save(binding, "UNKNOWN", None, "Lookup unavailable; no create attempted")
        if not listing.complete:
            return self._save(binding, "UNKNOWN", None, "Incomplete lookup; no create attempted")
        # The lookup itself is checked, not trusted to silently discard duplicates.
        if any(p.parent_id != self.parent or p.key != binding.key for p in listing.pages):
            return self._save(binding, "MISMATCH", None, "Lookup returned unbound records; no write")
        if len(listing.pages) > 1:
            return self._save(binding, "AMBIGUOUS", None, "Multiple matching pages; preserve all and hold")
        if listing.pages:
            return self._readback(binding, listing.pages[0].page_id)
        if row:
            # Even a complete lookup cannot prove that an earlier remote create
            # did not happen; Notion search/list observations can be delayed.
            return self._save(binding, "UNKNOWN", None, "No match after prior attempt or hold; never recreate automatically")
        self._save(binding, "CREATE_INTENT", None, "Durable intent recorded before external create")
        try:
            page_id = self.transport.create_child(binding)
            if not isinstance(page_id, str) or not re.fullmatch(r"[0-9a-f]{32}", page_id.replace("-", "")):
                raise ValueError("Create returned no valid page identity")
        except Exception:
            return self._save(binding, "UNKNOWN", None, "Create outcome uncertain; reconcile only, never blind retry")
        self._save(binding, "ACKNOWLEDGED", page_id, "Create acknowledged; readback still required")
        return self._readback(binding, page_id)
