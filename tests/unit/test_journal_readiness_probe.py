"""Offline host-readiness probe tests; no live destination or workflow activation."""
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from tools.journal_readiness_probe import evaluate, main


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "journal.sqlite"
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE runner_identity (identity TEXT, config TEXT)")
            db.execute("INSERT INTO runner_identity VALUES ('synthetic-host','{}')")
            db.execute("CREATE TABLE runner_inbox (key TEXT PRIMARY KEY, run TEXT, state TEXT)")
            db.execute("INSERT INTO runner_inbox VALUES ('run-1', '{}', 'HOLD')")
        self.path.chmod(0o600)

    def test_readiness_is_observation_only_not_activation(self):
        before = self.path.read_bytes()
        report = evaluate(self.path, "synthetic-host")
        self.assertEqual(report["verdict"], "LOCAL_JOURNAL_OBSERVED_NOT_ACTIVATED")
        self.assertEqual(report["journal"]["pending_or_held"], 1)
        self.assertEqual(report["passive_schedule"], "DISABLED")
        self.assertEqual(report["active_triggers"], "DISABLED")
        self.assertEqual(report["notion_writes"], "DISABLED")
        self.assertEqual(report["cortex_writes"], "DISABLED")
        self.assertEqual(self.path.read_bytes(), before)

    def test_missing_journal_holds_and_does_not_reinitialize(self):
        self.path.unlink()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(["--journal", str(self.path), "--identity", "synthetic-host"])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(output.getvalue())["verdict"], "HOLD")
        self.assertFalse(self.path.exists())

    def test_wrong_identity_holds_without_details(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(["--journal", str(self.path), "--identity", "wrong"])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(output.getvalue())["reason"], "JOURNAL_CUSTODY_NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main()
