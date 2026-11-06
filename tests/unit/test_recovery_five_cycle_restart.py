"""Five real process-restart cycles against one durable synthetic SQLite file.

No provider clients, credentials, network, workflow edits or live effects.
This tests TranscriptCoordinator persistence, not an event dedupe ledger,
remote fencing, authenticated provider readback or CP09.
"""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from nexus_sandbox.transcript_ingestion import STAGES, TranscriptCoordinator

VIDEO = "kokDVXUGdes"
RAW = "synthetic transcript: recovery-only fixture"
EVIDENCE = {"destination": "synthetic:notion", "readback": "synthetic:observed"}


def worker(db, action):
    script = """
import sys
from nexus_sandbox.transcript_ingestion import TranscriptCoordinator, STAGES
c = TranscriptCoordinator(sys.argv[1])
try:
    key = c.receive('kokDVXUGdes', 'synthetic transcript: recovery-only fixture')
    if sys.argv[2] == 'complete':
        c.record(key, STAGES[1], 'COMPLETE',
                 {'destination':'synthetic:notion','readback':'synthetic:observed'},
                 independently_read_back=True)
    elif sys.argv[2] == 'conflict':
        try:
            c.record(key, STAGES[1], 'COMPLETE',
                     {'destination':'synthetic:other','readback':'synthetic:other'},
                     independently_read_back=True)
        except ValueError:
            sys.exit(0)
        sys.exit(2)
    elif sys.argv[2] == 'alter':
        try:
            c.receive('kokDVXUGdes', 'conflicting transcript')
        except ValueError:
            sys.exit(0)
        sys.exit(3)
    print(c.receipt(key)['next_stage'])
finally:
    c.close()
"""
    env = dict(os.environ)
    # The test runner already imports nexus_sandbox; provide that same root
    # to actual child Python interpreters without installing dependencies.
    import nexus_sandbox
    root = str(Path(nexus_sandbox.__file__).resolve().parent.parent)
    env["PYTHONPATH"] = root
    return subprocess.run([sys.executable, "-c", script, db, action],
                          capture_output=True, text=True, env=env, timeout=20)


class FiveCycleRestartTests(unittest.TestCase):
    def test_five_separate_process_cycles_and_independent_sqlite_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "persistent.sqlite3")
            expected_hash = hashlib.sha256(RAW.encode()).hexdigest()
            initial_receipt = None
            for cycle in range(5):
                # Each invocation is a separate interpreter and SQLite connection.
                action = "complete" if cycle == 0 else "replay"
                result = worker(db, action)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), STAGES[2])
                with sqlite3.connect(db) as independent:
                    self.assertEqual(independent.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                    sources = independent.execute("SELECT id,raw_sha256 FROM source").fetchall()
                    rows = independent.execute(
                        "SELECT stage,status,verified,evidence_json,recorded_at "
                        "FROM checkpoint ORDER BY stage").fetchall()
                self.assertEqual(sources, [("youtube:" + VIDEO, expected_hash)])
                self.assertEqual(len(rows), 2)
                self.assertEqual({r[0] for r in rows}, set(STAGES[:2]))
                verified = next(r for r in rows if r[0] == STAGES[1])
                self.assertEqual(verified[1:3], ("COMPLETE", 1))
                self.assertEqual(json.loads(verified[3]), EVIDENCE)
                if initial_receipt is None:
                    initial_receipt = verified
                else:
                    self.assertEqual(verified, initial_receipt)
                self.assertEqual(worker(db, "conflict").returncode, 0)
                self.assertEqual(worker(db, "alter").returncode, 0)

    def test_unverified_stage_after_restart_is_not_promoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "persistent.sqlite3")
            c = TranscriptCoordinator(db)
            key = c.receive(VIDEO, RAW)
            c.record(key, STAGES[1], "BLOCKED", {"reason": "synthetic:uncertain"})
            c.close()
            r = worker(db, "replay")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), STAGES[1])
            c = TranscriptCoordinator(db)
            try:
                self.assertEqual(c.receipt(key)["status"], "INCOMPLETE")
                self.assertEqual(c.get(key, STAGES[1]).status, "BLOCKED")
            finally:
                c.close()
