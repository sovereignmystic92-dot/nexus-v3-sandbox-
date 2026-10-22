"""Owned synthetic child process used only for SIGKILL recovery checks."""

import argparse
import json
from pathlib import Path
import signal
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nexus_sandbox.contracts import Request
from nexus_sandbox.coordinator import SQLiteCoordinator, digest


def ready():
    print("READY", flush=True)
    signal.pause()
    raise RuntimeError("Fault worker unexpectedly resumed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("database")
    parser.add_argument("mode", choices=("after-archive", "during-output", "after-output"))
    args = parser.parse_args()
    fixture = json.loads((Path(__file__).resolve().parents[1] / "tests/fixtures/complete-source.json").read_text())
    coordinator = SQLiteCoordinator(args.database, [fixture], case_id="FAULT-WORKER")
    request = Request(fixture["idempotency_key"], fixture["source_id"], fixture["source_revision"],
                      fixture["destination_id"], digest(fixture["payload"]), True)
    cp = coordinator.submit(request)
    original_event = coordinator._event
    if args.mode == "during-output":
        def interrupt(db, row, *rest, **kwargs):
            if row["state"] == "OUTPUT_CREATED":
                ready()  # Artifact/checkpoint written inside transaction; commit not reached.
            return original_event(db, row, *rest, **kwargs)
        coordinator._event = interrupt
    coordinator.resume(cp.transaction_id, cp.version)
    ready()  # The requested transition has committed.


if __name__ == "__main__":
    main()
