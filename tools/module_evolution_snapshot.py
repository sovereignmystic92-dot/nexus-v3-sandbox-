"""Portable, verified offline snapshots for Nexus module event receipts.

Snapshots can be moved between isolated jobs by an explicitly authorized
transport. This module itself does not upload, download, or authenticate.
"""
import hashlib
import json
from pathlib import Path
import sqlite3

VERSION = "module_evolution_snapshot_v1"
MAX_RECEIPTS = 100000


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _validate_row(row):
    key, event_json, modules_json, status = row
    if not isinstance(key, str) or len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
        raise ValueError("invalid event key")
    if status != "PENDING_VALIDATION":
        raise ValueError("unsupported receipt status")
    envelope = json.loads(event_json)
    modules = json.loads(modules_json)
    if not isinstance(envelope, dict) or not isinstance(modules, list):
        raise ValueError("invalid receipt")
    from module_evolution_runner import MODULES, EVENTS
    required = ("repository", "event", "event_id", "subject")
    if envelope.get("repository") != "sovereignmystic92-dot/nexus-v3-sandbox-" or envelope.get("event") not in EVENTS:
        raise ValueError("untrusted repository/event")
    if any(not isinstance(envelope.get(k), str) or not envelope[k] for k in required):
        raise ValueError("missing receipt identity")
    expected = hashlib.sha256(json.dumps([envelope[k] for k in required], separators=(",", ":")).encode()).hexdigest()
    if expected != key or modules != sorted(set(modules)) or any(m not in MODULES for m in modules):
        raise ValueError("receipt mismatch")
    if canonical(envelope) != event_json or json.dumps(modules) != modules_json:
        raise ValueError("noncanonical receipt")
    return row


def export_snapshot(database):
    with sqlite3.connect(database) as db:
        rows = db.execute("SELECT event_key, event_json, modules_json, status FROM event_receipts ORDER BY event_key").fetchall()
    if len(rows) > MAX_RECEIPTS:
        raise ValueError("too many receipts")
    records = [dict(zip(("event_key", "event_json", "modules_json", "status"), _validate_row(row))) for row in rows]
    payload = {"schema": VERSION, "receipts": records}
    return {"payload": payload, "sha256": hashlib.sha256(canonical(payload).encode()).hexdigest()}


def import_snapshot(database, snapshot):
    if not isinstance(snapshot, dict) or set(snapshot) != {"payload", "sha256"}:
        raise ValueError("invalid snapshot")
    payload = snapshot["payload"]
    if not isinstance(payload, dict) or payload.get("schema") != VERSION or not isinstance(payload.get("receipts"), list):
        raise ValueError("invalid snapshot schema")
    if len(payload["receipts"]) > MAX_RECEIPTS:
        raise ValueError("too many receipts")
    if hashlib.sha256(canonical(payload).encode()).hexdigest() != snapshot["sha256"]:
        raise ValueError("snapshot digest mismatch")
    rows = []
    for item in payload["receipts"]:
        if not isinstance(item, dict) or set(item) != {"event_key", "event_json", "modules_json", "status"}:
            raise ValueError("invalid receipt structure")
        rows.append(_validate_row(tuple(item[k] for k in ("event_key", "event_json", "modules_json", "status"))))
    keys = [row[0] for row in rows]
    if keys != sorted(set(keys)):
        raise ValueError("unsorted or duplicated receipts")
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE IF NOT EXISTS event_receipts (event_key TEXT PRIMARY KEY, event_json TEXT NOT NULL, modules_json TEXT NOT NULL, status TEXT NOT NULL)")
        for row in rows:
            existing = db.execute("SELECT event_json, modules_json, status FROM event_receipts WHERE event_key=?", (row[0],)).fetchone()
            if existing is not None and existing != row[1:]:
                raise ValueError("conflicting existing receipt")
        db.executemany("INSERT OR IGNORE INTO event_receipts VALUES (?,?,?,?)", rows)
    return len(rows)


def save_snapshot(database, destination):
    snapshot = export_snapshot(database)
    Path(destination).write_text(canonical(snapshot) + "\n", encoding="utf-8")
    return snapshot["sha256"]


def load_snapshot(database, source):
    return import_snapshot(database, json.loads(Path(source).read_text(encoding="utf-8")))
