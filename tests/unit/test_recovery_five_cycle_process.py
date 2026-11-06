"""Five real-process SQLite restart cycles; synthetic data and zero provider calls.

The worker exits abruptly after committing its checkpoint. A separate process
reopens the same on-disk journal, checks integrity, and attempts safe retries.
This validates local persistence only, not cross-host fencing or live delivery.
"""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from nexus_sandbox.transcript_ingestion import STAGES, digest_source

SRC = str(Path(__file__).resolve().parents[2] / "src")
WORKER = r"""
import json, os, sys
from nexus_sandbox.transcript_ingestion import TranscriptCoordinator, STAGES
path, video, body, phase = sys.argv[1:]
c = TranscriptCoordinator(path)
key = c.receive(video, body)
evidence = {"destination": "synthetic:notion:" + video,
            "readback": "synthetic:receipt:" + video}
if phase == "interrupt":
    c.record(key, STAGES[1], "COMPLETE", evidence, independently_read_back=True)
    os._exit(23)  # no close, destructor, or Python cleanup
assert c.get(key, STAGES[1]).evidence == evidence
before = c.get(key, STAGES[1])
again = c.record(key, STAGES[1], "COMPLETE", evidence, independently_read_back=True)
assert before == again
try:
    c.record(key, STAGES[1], "COMPLETE",
             {"destination": "synthetic:other", "readback": "synthetic:other"},
             independently_read_back=True)
except ValueError:
    pass
else:
    raise AssertionError("Conflicting verified receipt accepted")
try:
    c.receive(video, body + " changed")
except ValueError:
    pass
else:
    raise AssertionError("Conflicting source accepted")
try:
    c.record(key, STAGES[1], "BLOCKED", {"error": "retry"})
except ValueError:
    pass
else:
    raise AssertionError("Verified checkpoint downgraded")
assert c.next_stage(key) == STAGES[2]
print(json.dumps(c.receipt(key), sort_keys=True))
c.close()
"""


class FiveCycleProcessRecoveryTests(unittest.TestCase):
    def test_five_distinct_abrupt_exit_restart_and_readback_cycles(self):
        with tempfile.TemporaryDirectory() as root:
            for cycle in range(5):
                with self.subTest(cycle=cycle + 1):
                    db = os.path.join(root, "cycle-%d.sqlite3" % cycle)
                    video = "rcvr%07d" % cycle  # exactly 11-character video ID
                    body = "synthetic transcript cycle %d" % cycle
                    env = dict(os.environ, PYTHONPATH=SRC)
                    args = [sys.executable, "-c", WORKER, db, video, body]
                    interrupted = subprocess.run(
                        args + ["interrupt"], env=env, capture_output=True,
                        text=True, timeout=15, check=False)
                    self.assertEqual(interrupted.returncode, 23, interrupted.stderr)
                    with sqlite3.connect(db) as observer:
                        self.assertEqual(observer.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                        self.assertEqual(observer.execute(
                            "SELECT count(*) FROM source").fetchone()[0], 1)
                        self.assertEqual(observer.execute(
                            "SELECT count(*) FROM checkpoint").fetchone()[0], 2)
                        self.assertEqual(observer.execute(
                            "SELECT raw_sha256 FROM source").fetchone()[0], digest_source(body))
                        before = observer.execute(
                            "SELECT stage,status,verified,evidence_json,recorded_at "
                            "FROM checkpoint ORDER BY stage").fetchall()
                    resumed = subprocess.run(
                        args + ["resume"], env=env, capture_output=True,
                        text=True, timeout=15, check=False)
                    self.assertEqual(resumed.returncode, 0, resumed.stderr)
                    receipt = json.loads(resumed.stdout)
                    self.assertEqual(receipt["next_stage"], STAGES[2])
                    self.assertEqual(receipt["status"], "INCOMPLETE")
                    with sqlite3.connect(db) as observer:
                        self.assertEqual(observer.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                        after = observer.execute(
                            "SELECT stage,status,verified,evidence_json,recorded_at "
                            "FROM checkpoint ORDER BY stage").fetchall()
                    self.assertEqual(before, after, "Replay mutated committed checkpoint")


if __name__ == "__main__":
    unittest.main()
