"""Real child-process kills and a bounded, dedicated tmpfs ENOSPC check."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import errno
import json
import os
from pathlib import Path
import select
import signal
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nexus_sandbox.contracts import Request
from nexus_sandbox.coordinator import SQLiteCoordinator, digest


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def request_for(fixture):
    return Request(fixture["idempotency_key"], fixture["source_id"], fixture["source_revision"],
                   fixture["destination_id"], digest(fixture["payload"]), True)


def advance(coordinator, request, target):
    cp = coordinator.submit(request)
    for _ in range(6):
        if cp.state == target:
            return cp
        require(cp.disposition == "OPEN", "Unexpected hold in fault check")
        cp = coordinator.resume(cp.transaction_id, cp.version)
    raise RuntimeError("Fault check did not reach target")


def snapshot(path):
    with closing(sqlite3.connect(path)) as db:
        return {table: db.execute("SELECT * FROM " + table + " ORDER BY rowid").fetchall()
                for table in ("transactions", "artifacts", "events", "attempts")}


def integrity(path):
    with closing(sqlite3.connect(path)) as db:
        return db.execute("PRAGMA integrity_check").fetchone()[0]


def kill_check(fixture, mode):
    with tempfile.TemporaryDirectory(prefix="nexus-kill-") as temporary:
        path = Path(temporary) / "synthetic.sqlite"
        coordinator = SQLiteCoordinator(path, [fixture], case_id="FAULT-" + mode)
        request = request_for(fixture)
        initial = "VALIDATED" if mode == "after-archive" else "ARCHIVED"
        before = advance(coordinator, request, initial)
        baseline = snapshot(path)
        with subprocess.Popen([sys.executable, "-B", str(ROOT / "tools/fault_worker.py"), str(path), mode],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as child:
            try:
                require(bool(select.select([child.stdout], [], [], 10)[0]), "Worker did not reach requested boundary")
                require(child.stdout.readline().strip() == "READY", "Worker failed before fault boundary")
                child.kill()  # Only this owned child PID is signalled.
                child.wait(timeout=5)
                require(child.returncode == -signal.SIGKILL, "SIGKILL termination not observed")
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)
        recovered = SQLiteCoordinator(path, [fixture], case_id="FAULT-RECOVERY")
        cp = recovered.submit(request)
        expected = "ARCHIVED" if mode in ("after-archive", "during-output") else "OUTPUT_CREATED"
        require(cp.state == expected, "Unexpected durable checkpoint after SIGKILL")
        if mode == "during-output":
            require(snapshot(path) == baseline and cp == before, "Uncommitted write survived process kill")
        require(integrity(path) == "ok", "Database integrity failed after SIGKILL")
        final = advance(recovered, request, "VERIFIED")
        records = snapshot(path)
        require(len(records["artifacts"]) == 3 and len(records["events"]) == 6
                and len(records["attempts"]) == 6, "Duplicate or missing records after recovery")
        require(records["artifacts"][0][0] == before.transaction_id + ":archive", "Archive identity changed")
        return {"case_id": "SIGKILL-" + mode, "status": "PASSED", "observed_signal": "SIGKILL",
                "recovered_checkpoint": cp.state, "final_state": final.state,
                "integrity_check": "ok", "artifacts": 3, "events": 6, "attempts": 6}


def disk_full_check(fixture):
    volume = Path("/fault-storage")
    mounts = [line.split() for line in Path("/proc/mounts").read_text().splitlines()]
    require(any(m[1] == str(volume) and m[2] == "tmpfs" for m in mounts), "Dedicated fault tmpfs is required")
    stats = os.statvfs(volume)
    capacity = stats.f_blocks * stats.f_frsize
    require(0 < capacity <= 8 * 1024 * 1024 and os.stat(volume).st_dev != os.stat("/tmp").st_dev,
            "Fault volume must be separate and at most 8 MiB")
    # Never fill an arbitrary host path or the general test /tmp filesystem.
    with tempfile.TemporaryDirectory(prefix="nexus-full-", dir=volume) as temporary:
        path = Path(temporary) / "synthetic.sqlite"
        large = dict(fixture, payload="Fictional pressure reading. " * 24000)
        coordinator = SQLiteCoordinator(path, [large], case_id="REAL-TMPFS-ENOSPC")
        request = request_for(large)
        before = advance(coordinator, request, "VALIDATED")
        baseline = snapshot(path)
        filler = Path(temporary) / "bounded-filler"
        bytes_written = 0
        observed_errno = None
        sqlite_failure = None
        try:
            with filler.open("wb", buffering=0) as stream:
                while bytes_written <= capacity:
                    try:
                        written = stream.write(b"\0" * 65536)
                        bytes_written += written
                    except OSError as error:
                        observed_errno = error.errno
                        break
            require(observed_errno == errno.ENOSPC, "Filesystem ENOSPC was not observed")
            require(os.statvfs(volume).f_bavail == 0, "Fault volume is not actually full")
            try:
                coordinator.resume(before.transaction_id, before.version)
            except sqlite3.Error as error:
                sqlite_failure = {"sqlite_errorcode": getattr(error, "sqlite_errorcode", None),
                                  "sqlite_errorname": getattr(error, "sqlite_errorname", None)}
            require(sqlite_failure is not None, "Write incorrectly succeeded on full filesystem")
            require(sqlite_failure["sqlite_errorcode"] is not None
                    and sqlite_failure["sqlite_errorcode"] & 255 == sqlite3.SQLITE_FULL,
                    "Expected SQLITE_FULL was not observed")
        finally:
            filler.unlink(missing_ok=True)
        require(snapshot(path) == baseline, "Full-disk write changed the durable snapshot")
        require(integrity(path) == "ok", "Database integrity failed after ENOSPC")
        final = advance(SQLiteCoordinator(path, [large]), request, "VERIFIED")
        require(len(snapshot(path)["artifacts"]) == 3, "Duplicate output after freeing space")
        return {"case_id": "REAL-TMPFS-ENOSPC", "status": "PASSED", "volume_capacity_bytes": capacity,
                "filler_bytes_written": bytes_written, "observed_errno": "ENOSPC",
                **sqlite_failure, "checkpoint_preserved": True, "integrity_check": "ok",
                "final_state_after_freeing_space": final.state,
                "limitation": "Full tmpfs before archive write; not device loss or power interruption"}


def run(crash_only=False):
    fixture = json.loads((ROOT / "tests/fixtures/complete-source.json").read_text())
    report = {"started_at_utc": datetime.now(timezone.utc).isoformat(), "cases": [], "status": "FAILED"}
    try:
        for mode in ("after-archive", "during-output", "after-output"):
            report["cases"].append(kill_check(fixture, mode))
        if not crash_only:
            report["cases"].append(disk_full_check(fixture))
        report["status"] = "PASSED"
    except Exception as error:
        report["failure"] = type(error).__name__ + ": " + str(error)
    report["ended_at_utc"] = datetime.now(timezone.utc).isoformat()
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--crash-only", action="store_true")
    args = parser.parse_args()
    result = run(args.crash_only)
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASSED" else 1)
