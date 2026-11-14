"""Fail-closed offline reconciliation of a verified snapshot with a new event.

Transport authenticity is an external precondition. This code verifies snapshot
integrity and receipt consistency, not GitHub artifact ownership or run identity.
"""
import argparse
import json
from pathlib import Path
import tempfile

from module_evolution_snapshot import load_snapshot, save_snapshot
from module_evolution_runner import evaluate


def reconcile(previous, event, destination, expected_sha256):
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64 or any(
        c not in "0123456789abcdef" for c in expected_sha256
    ):
        raise ValueError("expected checkpoint digest required")
    if Path(destination).exists():
        raise ValueError("destination must not already exist")
    with tempfile.TemporaryDirectory() as tmp:
        database = Path(tmp) / "receipts.sqlite"
        import json as _json
        snapshot = _json.loads(Path(previous).read_text(encoding="utf-8"))
        if snapshot.get("sha256") != expected_sha256:
            raise ValueError("checkpoint digest does not match trusted expectation")
        previous_count = load_snapshot(database, previous)
        receipt = evaluate(database, event)
        next_digest = save_snapshot(database, Path(tmp) / "next.json")
        next_snapshot = json.loads((Path(tmp) / "next.json").read_text(encoding="utf-8"))
        next_count = len(next_snapshot["payload"]["receipts"])
        if next_count not in (previous_count, previous_count + 1):
            raise ValueError("unexpected receipt delta")
        # Exclusive creation after validation; caller controls destination directory.
        with Path(destination).open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(next_snapshot, sort_keys=True, separators=(",", ":")) + "\n")
    return {"previous_receipts": previous_count, "receipts": next_count,
            "new_receipts": next_count - previous_count, "checkpoint_sha256": next_digest,
            "event_key": receipt["event_key"], "readiness_advanced": False,
            "transport_authenticated": False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--previous", required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--event-file", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    event = json.loads(Path(a.event_file).read_text(encoding="utf-8"))
    print(json.dumps(reconcile(a.previous, event, a.output, a.expected_sha256), sort_keys=True))


if __name__ == "__main__":
    main()
