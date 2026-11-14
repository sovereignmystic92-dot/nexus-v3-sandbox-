"""Bounded, offline-only GitHub event evaluation for Nexus modules.

This evaluator records observations, NOT verified module advancement.
No network calls, credentials, provider writes, or autonomous grants.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

MODULES = ("skill_forge", "personal_growth_forge", "field_journal",
           "civilization_engine", "trading_platform")
EVENTS = frozenset(("push", "pull_request", "issues", "workflow_run"))

def evaluate(db_path, envelope):
    if not isinstance(envelope, dict):
        raise ValueError("event must be an object")
    required = ("repository", "event", "event_id", "subject", "source_url")
    if any(not isinstance(envelope.get(k), str) or not envelope[k].strip() for k in required):
        raise ValueError("missing event provenance")
    if envelope["event"] not in EVENTS:
        raise ValueError("unsupported event")
    if envelope["repository"] != "sovereignmystic92-dot/nexus-v3-sandbox-":
        raise ValueError("unexpected repository")
    # Event labels are untrusted hints. Never infer readiness from them.
    hints = envelope.get("module_hints", [])
    if not isinstance(hints, list) or any(m not in MODULES for m in hints):
        raise ValueError("unknown module hint")
    modules = sorted(set(hints))
    key = hashlib.sha256(json.dumps(
        [envelope[k] for k in required[:4]], separators=(",", ":")
    ).encode()).hexdigest()
    db_path = Path(db_path)
    with sqlite3.connect(db_path) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("""CREATE TABLE IF NOT EXISTS event_receipts
                   (event_key TEXT PRIMARY KEY, event_json TEXT NOT NULL,
                    modules_json TEXT NOT NULL, status TEXT NOT NULL)""")
        canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        db.execute("INSERT OR IGNORE INTO event_receipts VALUES (?, ?, ?, ?)",
                   (key, canonical, json.dumps(modules), "PENDING_VALIDATION"))
        saved = db.execute("SELECT event_json, modules_json, status FROM event_receipts WHERE event_key=?",
                           (key,)).fetchone()
        if saved[0] != canonical:
            raise ValueError("event identity collision or changed payload")
    return {"event_key": key, "modules": json.loads(saved[1]), "status": saved[2],
            "evidence_class": "offline", "readiness_advanced": False}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--database", required=True)
    p.add_argument("--event-file", required=True)
    a = p.parse_args()
    print(json.dumps(evaluate(a.database, json.loads(Path(a.event_file).read_text()))))

if __name__ == "__main__":
    main()
