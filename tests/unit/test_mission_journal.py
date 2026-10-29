"""Synthetic persistence and interruption tests; no external system writes."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from nexus_sandbox.mission_dispatcher import Mission
from nexus_sandbox.mission_journal import MissionJournal


class MissionJournalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "missions.sqlite"
        self.mission = Mission("synthetic-mission", "PASSIVE", "fixture-event",
                               ("source-verified",), ("inspect", "verify"))
        self.journal = MissionJournal.provision(self.path, "fixture-identity")

    def record(self, **overrides):
        args = dict(observed_triggers=("fixture-event",),
                    satisfied_dependencies=("source-verified",))
        args.update(overrides)
        return self.journal.record(self.mission, **args)

    def test_progress_is_replayed_without_any_execution(self):
        first = self.record()
        self.assertEqual(first["decision"]["state"], "READY")
        self.assertEqual(first["revision"], 1)
        self.assertIn("inspect", first["decision"]["next_action"])
        reopened = MissionJournal(self.path, "fixture-identity")
        self.assertEqual(reopened.observe(self.mission.mission_id), first)
        second = reopened.record(self.mission,
            observed_triggers=("fixture-event",),
            satisfied_dependencies=("source-verified",),
            verified_steps=("inspect",), expected_revision=1)
        self.assertIn("verify", second["decision"]["next_action"])
        self.assertEqual(second["revision"], 2)
        final = reopened.record(self.mission,
            observed_triggers=("fixture-event",),
            satisfied_dependencies=("source-verified",),
            verified_steps=("inspect", "verify"), expected_revision=2)
        self.assertEqual(final["decision"]["state"], "COMPLETE")
        self.assertEqual(reopened.observe(self.mission.mission_id), final)

    def test_idempotent_replay_does_not_append(self):
        first = self.record()
        repeated = self.record()
        self.assertEqual(repeated, first)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM mission_events").fetchone()[0], 1)

    def test_stale_revision_is_blocked(self):
        self.record()
        with self.assertRaises(ValueError):
            self.record(verified_steps=("inspect",), expected_revision=0)
        self.assertEqual(self.journal.observe(self.mission.mission_id)["revision"], 1)

    def test_missing_journal_is_not_recreated(self):
        self.path.unlink()
        with self.assertRaises(FileNotFoundError):
            MissionJournal(self.path, "fixture-identity")
        self.assertFalse(self.path.exists())

    def test_wrong_identity_and_contract_change_fail(self):
        with self.assertRaises(ValueError):
            MissionJournal(self.path, "wrong")
        self.record()
        changed = Mission(self.mission.mission_id, "PASSIVE", "fixture-event",
                          ("source-verified",), ("different",))
        with self.assertRaises(ValueError):
            self.journal.record(changed, expected_revision=1)

    def test_evidence_retraction_and_hold_release_not_silent(self):
        first = self.record(blocked_steps=("inspect",))
        self.assertEqual(first["decision"]["state"], "HOLD")
        with self.assertRaises(ValueError):
            self.record(expected_revision=1)
        self.assertEqual(self.journal.observe(self.mission.mission_id), first)

    def test_canonical_hash_tamper_detected(self):
        self.record()
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE mission_events SET payload='{}'")
        with self.assertRaises(ValueError):
            self.journal.observe(self.mission.mission_id)

    def test_private_file_and_directory_required(self):
        self.path.chmod(0o644)
        with self.assertRaises(ValueError):
            MissionJournal(self.path, "fixture-identity")
        self.path.chmod(0o600)
        os.chmod(self.directory.name, 0o755)
        with self.assertRaises(ValueError):
            MissionJournal(self.path, "fixture-identity")

    def test_distinct_process_reads_journal_from_previous_process(self):
        first = self.record()
        root = Path(__file__).resolve().parents[2]
        program = ("import json,sys;"
                   "from nexus_sandbox.mission_journal import MissionJournal;"
                   "j=MissionJournal(sys.argv[1],'fixture-identity');"
                   "print(json.dumps(j.observe('synthetic-mission'),sort_keys=True))")
        outcome = subprocess.run([sys.executable, "-c", program, str(self.path)],
                                 cwd=root, env=dict(os.environ, PYTHONPATH=str(root / "src")),
                                 capture_output=True, text=True, timeout=10)
        self.assertEqual(outcome.returncode, 0, outcome.stderr)
        self.assertEqual(json.loads(outcome.stdout), first)


if __name__ == "__main__":
    unittest.main()
