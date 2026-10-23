"""Single-worker synthetic Cortex persistence; no network or credentials.

The host supplies a transport. Sequential reads do not provide atomic version
checks. An uncertain write is reconciled by name and never repeated blindly.
"""

from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from sqlite3 import connect
from typing import Protocol

MARKER = "TEST FIXTURE — SYNTHETIC — NOT CANONICAL."


class BindingConflict(ValueError):
    pass


class JournalIntegrityError(ValueError):
    """Stop for trusted journal recovery; never reset identity automatically."""


@dataclass(frozen=True)
class Module:
    id: str
    name: str
    version: int
    content: str
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class Write:
    key: str
    name: str
    content: str
    dependencies: tuple[str, ...]
    source: Module
    before: Module | None = None


@dataclass(frozen=True)
class Outcome:
    operation_outcome: str
    protocol_verdict: str
    checkpoint: str
    module_id: str | None
    module_version: int | None
    reason: str


class Transport(Protocol):
    # None means explicit service-reported absence, never a read outage.
    def get(self, name: str) -> Module | None: ...
    def create(self, name: str, content: str, dependencies: tuple[str, ...]): ...
    def update(self, name: str, content: str, dependencies: tuple[str, ...]): ...


def valid_module(module):
    return (type(module) is Module and isinstance(module.id, str) and bool(module.id)
            and isinstance(module.name, str) and type(module.version) is int and module.version > 0
            and isinstance(module.content, str) and type(module.dependencies) is tuple
            and all(isinstance(d, str) for d in module.dependencies))


class CortexAdapter:
    def __init__(self, journal: Path, allowed_names: frozenset[str], transport: Transport):
        if (type(allowed_names) is not frozenset or not allowed_names
                or any(not isinstance(n, str) or not n.startswith("Nexus Sandbox ") for n in allowed_names)):
            raise ValueError("Explicit synthetic module-name allowlist required")
        self.names = allowed_names
        self.transport = transport
        self.journal = Path(journal)
        with closing(self._db()) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS cortex_receipts (
                    key TEXT PRIMARY KEY, binding TEXT NOT NULL,
                    intent_sent INTEGER NOT NULL, receipt TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS cortex_identity_anchors (
                    key TEXT PRIMARY KEY, module_id TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS cortex_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL,
                    receipt TEXT NOT NULL, observed_at_utc TEXT NOT NULL);
            """)

    def _db(self):
        return connect(self.journal)

    def _validate(self, request):
        if type(request) is not Write or not re.fullmatch(r"synthetic:request:[A-Za-z0-9_-]+", request.key):
            raise ValueError("Synthetic immutable write key required")
        if (request.name not in self.names or type(request.dependencies) is not tuple
                or any(d not in self.names or d == request.name for d in request.dependencies)
                or len(set(request.dependencies)) != len(request.dependencies)
                or not isinstance(request.content, str) or not request.content.startswith(MARKER)
                or request.key not in request.content or len(request.content.encode()) > 65536):
            raise ValueError("Write outside explicit synthetic scope")
        if (not valid_module(request.source) or request.source.name not in self.names
                or request.source.name == request.name or not request.source.content.startswith(MARKER)
                or any(d not in self.names for d in request.source.dependencies)):
            raise ValueError("Exact synthetic source binding required")
        if request.before is not None:
            if (not valid_module(request.before) or request.before.name != request.name
                    or request.before.id == request.source.id or not request.before.content.startswith(MARKER)
                    or any(d not in self.names for d in request.before.dependencies)):
                raise ValueError("Exact synthetic target baseline required for update")

    def _save(self, request, outcome, sent):
        binding = json.dumps(asdict(request), sort_keys=True)
        receipt = json.dumps(asdict(outcome), sort_keys=True)
        with closing(self._db()) as db, db:
            old = db.execute("SELECT binding,intent_sent FROM cortex_receipts WHERE key=?", (request.key,)).fetchone()
            if old and old[0] != binding:
                raise BindingConflict("Key is bound to another request")
            if outcome.protocol_verdict == "VERIFIED":
                anchor = db.execute("SELECT module_id FROM cortex_identity_anchors WHERE key=?", (request.key,)).fetchone()
                if not isinstance(outcome.module_id, str) or not outcome.module_id:
                    raise JournalIntegrityError("Journal integrity: verification lacks identity")
                if anchor and anchor[0] != outcome.module_id:
                    raise JournalIntegrityError("Journal integrity: verified identity conflicts with anchor")
                if not anchor:
                    db.execute("INSERT INTO cortex_identity_anchors VALUES(?,?)", (request.key, outcome.module_id))
            sent = bool(sent or old and old[1])
            db.execute("INSERT INTO cortex_receipts VALUES(?,?,?,?) ON CONFLICT(key) DO UPDATE SET intent_sent=excluded.intent_sent,receipt=excluded.receipt",
                       (request.key, binding, int(sent), receipt))
            db.execute("INSERT INTO cortex_events(key,receipt,observed_at_utc) VALUES(?,?,?)",
                       (request.key, receipt, datetime.now(timezone.utc).isoformat()))
        return outcome

    @staticmethod
    def _desired(request, module, known_id=None):
        expected_version = request.before.version + 1 if request.before else 1
        return (valid_module(module) and module.name == request.name
                and module.content == request.content and module.dependencies == request.dependencies
                and module.version == expected_version
                and (known_id is None or module.id == known_id)
                and (request.before is None or module.id == request.before.id))

    def _get(self, name):
        if name not in self.names:
            raise ValueError("Read outside allowlist")
        module = self.transport.get(name)
        if module is not None and (not valid_module(module) or module.name != name):
            raise ValueError("Malformed or misidentified transport result")
        return module

    @staticmethod
    def _journal_identity(db, key, row):
        # This detects inconsistent retained records, not coherent tampering or
        # replacement/loss of the entire database. Legacy migration trusts history.
        events = [json.loads(encoded) for (encoded,) in db.execute(
            "SELECT receipt FROM cortex_events WHERE key=? ORDER BY sequence", (key,))]
        if any(not isinstance(event, dict) for event in events):
            raise JournalIntegrityError("Journal integrity: malformed event")
        anchor = db.execute("SELECT module_id FROM cortex_identity_anchors WHERE key=?", (key,)).fetchone()
        if row is None:
            if events or anchor:
                raise JournalIntegrityError("Journal integrity: orphaned history or identity anchor")
            return None
        if not events or events[-1] != json.loads(row[2]):
            raise JournalIntegrityError("Journal integrity: missing history or latest receipt mismatch")
        identity = None
        for event in events:
            if event.get("protocol_verdict") == "VERIFIED":
                identity = event.get("module_id")
                if not isinstance(identity, str) or not identity:
                    raise JournalIntegrityError("Journal integrity: verified event lacks identity")
                break
        if anchor:
            if not isinstance(anchor[0], str) or not anchor[0] or anchor[0] != identity:
                raise JournalIntegrityError("Journal integrity: identity history missing or conflicts with anchor")
        elif identity is not None:
            # Backfill complete trusted legacy history before any transport call.
            db.execute("INSERT INTO cortex_identity_anchors VALUES(?,?)", (key, identity))
        return identity

    def ensure(self, request: Write):
        self._validate(request)
        binding = json.dumps(asdict(request), sort_keys=True)
        with closing(self._db()) as db, db:
            row = db.execute("SELECT binding,intent_sent,receipt FROM cortex_receipts WHERE key=?", (request.key,)).fetchone()
            if row and row[0] != binding:
                raise BindingConflict("Key is bound to another request")
            identity = self._journal_identity(db, request.key, row)
            if request.before is not None and identity is not None and identity != request.before.id:
                raise JournalIntegrityError("Journal integrity: anchor conflicts with update baseline")
            known_id = request.before.id if request.before is not None else identity
        prior = json.loads(row[2]) if row else {}
        def save(operation, verdict, checkpoint, module=None, reason="", sent=False):
            return self._save(request, Outcome(operation, verdict, checkpoint,
                module.id if module else prior.get("module_id"),
                module.version if module else prior.get("module_version"), reason), sent)
        try:
            source = self._get(request.source.name)
            target = self._get(request.name)
        except Exception:
            return save("NOT_ATTEMPTED", "UNKNOWN", "READ_BLOCKED", reason="Read unavailable or malformed; no write")
        if source != request.source:
            return save("NOT_ATTEMPTED", "BLOCKED", "SOURCE_CHANGED", reason="Source identity/version/content/dependencies differ or source missing")
        wrote = False
        if not self._desired(request, target, known_id):
            if row and row[1]:
                return save("NOT_ATTEMPTED", "UNKNOWN", "RECONCILE_ONLY", target,
                            "Prior write intent; desired state not observed; never blind retry")
            if target != request.before:
                return save("NOT_ATTEMPTED", "BLOCKED", "TARGET_CONFLICT", target,
                            "Target differs from expected absent or exact update baseline")
            # Durable intent precedes any external side effect. DB failure here
            # propagates and no write occurs. There is no remote CAS parameter.
            save("NOT_ATTEMPTED", "NOT_TESTED", "WRITE_INTENT", target, "Intent committed before write", True)
            try:
                if request.before is None:
                    self.transport.create(request.name, request.content, request.dependencies)
                else:
                    self.transport.update(request.name, request.content, request.dependencies)
                wrote = True
            except Exception:
                return save("UNKNOWN", "UNKNOWN", "RECONCILE_ONLY", target,
                            "Write outcome uncertain; read by bound name before any further action", True)
        try:
            # Completion always uses new transport reads, never a write reply.
            final_source = self._get(request.source.name)
            final_target = self._get(request.name)
        except Exception:
            return save("SUCCEEDED" if wrote else "NOT_ATTEMPTED", "UNKNOWN", "READBACK_PENDING",
                        reason="Independent readback unavailable")
        operation = "SUCCEEDED" if wrote else "NOT_ATTEMPTED"
        if final_source != request.source:
            return save(operation, "BLOCKED", "SOURCE_CHANGED", final_target,
                        "Source changed during operation; completion withheld")
        if not self._desired(request, final_target, known_id):
            return save(operation, "FAILED", "READBACK_MISMATCH", final_target,
                        "Exact target identity/version/content/dependency readback mismatch; preserve remote state")
        return save(operation, "VERIFIED", "VERIFIED", final_target,
                    "Exact independent readback matched immutable binding")
