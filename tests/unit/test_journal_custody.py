"""Synthetic custody checks: no remote service, schedule, or repair."""
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from nexus_sandbox.journal_custody import inspect_journal


class CustodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "journal.sqlite"
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE runner_identity(identity TEXT, config TEXT)")
            db.execute("INSERT INTO runner_identity VALUES ('fixture', '{}')")
            db.execute("CREATE TABLE runner_inbox(key TEXT PRIMARY KEY, run TEXT, state TEXT)")
            db.execute("INSERT INTO runner_inbox VALUES ('a','{}','HOLD')")
            db.execute("INSERT INTO runner_inbox VALUES ('b','{}','VERIFIED')")
        self.path.chmod(0o600)

    def test_existing_journal_is_read_only_and_resumable(self):
        before = self.path.read_bytes()
        result = inspect_journal(self.path, "fixture")
        self.assertEqual(result["pending_or_held"], 1)
        self.assertEqual(result["verified"], 1)
        self.assertEqual(self.path.read_bytes(), before)

    def test_missing_journal_never_recreated(self):
        self.path.unlink()
        with self.assertRaises(FileNotFoundError):
            inspect_journal(self.path, "fixture")
        self.assertFalse(self.path.exists())

    def test_wrong_identity_fails(self):
        with self.assertRaises(ValueError):
            inspect_journal(self.path, "different")

    def test_symlink_and_world_readable_journal_fail(self):
        linked = self.path.with_name("alias.sqlite")
        linked.symlink_to(self.path)
        with self.assertRaises(ValueError):
            inspect_journal(linked, "fixture")
        linked.unlink()
        self.path.chmod(0o644)
        with self.assertRaises(ValueError):
            inspect_journal(self.path, "fixture")

    def test_unsafe_parent_fails(self):
        os.chmod(self.tmp.name, 0o755)
        with self.assertRaises(ValueError):
            inspect_journal(self.path, "fixture")

    def test_corruption_and_unknown_state_fail(self):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE runner_inbox SET state='OTHER'")
        with self.assertRaises(ValueError):
            inspect_journal(self.path, "fixture")
        self.path.write_bytes(b"not sqlite")
        with self.assertRaises(sqlite3.DatabaseError):
            inspect_journal(self.path, "fixture")


if __name__ == "__main__":
    unittest.main()
