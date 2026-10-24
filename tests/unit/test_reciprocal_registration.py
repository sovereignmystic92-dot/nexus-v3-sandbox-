"""CP18: typed reciprocal references on the declared local SQLite surface."""
from dataclasses import replace
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from nexus_sandbox.contracts import Request
from nexus_sandbox.coordinator import BindingConflict, SQLiteCoordinator, StaleCheckpoint, digest


class ReciprocalRegistrationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="nexus-reciprocal-")
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "state.sqlite"
        self.fixture = json.loads((Path(__file__).parents[1] / "fixtures/complete-source.json").read_text())
        self.c = SQLiteCoordinator(self.path, [self.fixture])
        f = self.fixture
        self.request = Request(f["idempotency_key"], f["source_id"], f["source_revision"],
                               f["destination_id"], digest(f["payload"]), f["source_complete"])
        self.cp = self.c.submit(self.request)
        while self.cp.state != "REGISTERED":
            self.cp = self.c.resume(self.cp.transaction_id, self.cp.version)
        self.tid = self.cp.transaction_id

    def sql(self, statement, values=()):
        with sqlite3.connect(self.path) as db:
            return db.execute(statement, values).fetchall()

    def snapshot(self):
        with sqlite3.connect(self.path) as db:
            return {t: db.execute("SELECT * FROM " + t + " ORDER BY 1,2").fetchall()
                    for t in ("transactions", "artifacts", "connections", "endpoint_references", "events", "attempts")}

    def hold(self, endpoint_type="derived_output"):
        self.sql("DELETE FROM endpoint_references WHERE endpoint_type=?", (endpoint_type,))
        self.cp = self.c.resume(self.tid, self.cp.version)
        self.assertEqual((self.cp.state, self.cp.disposition), ("REGISTERED", "INCOMPLETE"))

    def test_complete_typed_registration_and_exact_repeat(self):
        self.assertEqual(self.sql("SELECT relation,archive_id,output_id,version FROM connections"),
                         [("derived_from", self.tid + ":archive", self.tid + ":output", 1)])
        self.assertEqual(len(self.sql("SELECT * FROM endpoint_references")), 2)
        self.cp = self.c.resume(self.tid, self.cp.version)
        before = self.snapshot()
        reopened = SQLiteCoordinator(self.path, [self.fixture])
        self.assertEqual(reopened.submit(self.request), self.cp)
        self.assertEqual(reopened.repair_reciprocity(self.tid, self.cp.version), self.cp)
        self.assertEqual(reopened.resume(self.tid, self.cp.version), self.cp)
        self.assertEqual(self.snapshot(), before)

    def test_missing_output_reference_holds_then_bounded_repair_reuses_connection(self):
        self._repair_case("derived_output")

    def test_missing_archive_reference_holds_then_bounded_repair_reuses_connection(self):
        self._repair_case("source_archive")

    def _repair_case(self, missing_type):
        connection_id = self.sql("SELECT connection_id FROM connections")[0][0]
        artifacts = self.sql("SELECT * FROM artifacts ORDER BY artifact_id")
        self.hold(missing_type)
        self.cp = self.c.repair_reciprocity(self.tid, self.cp.version)
        self.assertEqual(self.cp.disposition, "INCOMPLETE")
        self.assertEqual(self.sql("SELECT connection_id,version FROM connections"), [(connection_id, 2)])
        self.assertEqual(self.sql("SELECT * FROM artifacts ORDER BY artifact_id"), artifacts)
        repaired = self.snapshot()
        self.assertEqual(self.c.repair_reciprocity(self.tid, self.cp.version), self.cp)
        self.assertEqual(self.snapshot(), repaired)
        envelope = json.loads(self.sql("SELECT envelope_json FROM attempts ORDER BY rowid DESC LIMIT 1")[0][0])
        self.assertEqual(envelope["operation_outcome"], "SUCCEEDED")
        self.assertNotEqual(envelope["protocol_verdict"], "VERIFIED")
        self.cp = SQLiteCoordinator(self.path, [self.fixture]).resume(self.tid, self.cp.version)
        self.assertEqual(self.cp.disposition, "VERIFIED")

    def test_both_missing_references_repaired_once(self):
        self.sql("DELETE FROM endpoint_references")
        self.cp = self.c.resume(self.tid, self.cp.version)
        self.cp = self.c.repair_reciprocity(self.tid, self.cp.version)
        self.assertEqual(len(self.sql("SELECT * FROM endpoint_references")), 2)
        self.assertEqual(self.c.resume(self.tid, self.cp.version).disposition, "VERIFIED")

    def test_wrong_endpoint_type_cannot_verify_or_be_repaired(self):
        self.sql("UPDATE endpoint_references SET endpoint_id=? WHERE endpoint_type='derived_output'", (self.tid + ":registry",))
        self.cp = self.c.resume(self.tid, self.cp.version)
        before = self.snapshot()
        self.assertEqual(self.cp.disposition, "INCOMPLETE")
        with self.assertRaises(BindingConflict):
            self.c.repair_reciprocity(self.tid, self.cp.version)
        self.assertEqual(self.snapshot(), before)

    def test_missing_connection_is_not_recreated(self):
        self.sql("DELETE FROM endpoint_references")
        self.sql("DELETE FROM connections")
        self.cp = self.c.resume(self.tid, self.cp.version)
        before = self.snapshot()
        with self.assertRaises(BindingConflict):
            self.c.repair_reciprocity(self.tid, self.cp.version)
        self.assertEqual(self.snapshot(), before)

    def test_changed_connection_binding_is_preserved(self):
        self.sql("UPDATE connections SET output_id=?", (self.tid + ":registry",))
        self.cp = self.c.resume(self.tid, self.cp.version)
        before = self.snapshot()
        with self.assertRaises(BindingConflict):
            self.c.repair_reciprocity(self.tid, self.cp.version)
        self.assertEqual(self.snapshot(), before)

    def test_repair_transaction_failure_rolls_back_references_connection_and_event(self):
        self.hold()
        self.sql("CREATE TRIGGER deny_repair BEFORE INSERT ON attempts BEGIN SELECT RAISE(ABORT,'synthetic fault'); END")
        before = self.snapshot()
        with self.assertRaises(sqlite3.IntegrityError):
            self.c.repair_reciprocity(self.tid, self.cp.version)
        self.assertEqual(self.snapshot(), before)
        self.sql("DROP TRIGGER deny_repair")
        self.cp = self.c.repair_reciprocity(self.tid, self.cp.version)
        self.assertEqual(self.c.resume(self.tid, self.cp.version).disposition, "VERIFIED")

    def test_stale_repair_version_denied_without_changes(self):
        self.hold()
        before = self.snapshot()
        with self.assertRaises(StaleCheckpoint):
            self.c.repair_reciprocity(self.tid, self.cp.version - 1)
        self.assertEqual(self.snapshot(), before)

    def test_changed_source_blocks_repair_without_changes(self):
        self.hold()
        changed = SQLiteCoordinator(self.path, [dict(self.fixture, payload="changed")])
        before = self.snapshot()
        with self.assertRaises(ValueError):
            changed.repair_reciprocity(self.tid, self.cp.version)
        self.assertEqual(self.snapshot(), before)

    def test_fresh_process_verifies_repaired_committed_reciprocity(self):
        self.hold()
        child_env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
        script = '''
import json,sys
from nexus_sandbox.coordinator import SQLiteCoordinator
c=SQLiteCoordinator(sys.argv[1],[json.loads(sys.argv[2])])
with c._connect() as reader:
    row=reader.execute("SELECT * FROM transactions WHERE transaction_id=?",(sys.argv[3],)).fetchone()
receipt=c._verify(row,json.loads(sys.argv[2])["payload"])
print(json.dumps(receipt))
'''
        # An actual fresh process must reject the missing endpoint before repair.
        before = self.snapshot()
        rejected = subprocess.run([sys.executable, "-c", script, str(self.path), json.dumps(self.fixture), self.tid],
                                  capture_output=True, text=True, check=True, timeout=15, env=child_env)
        self.assertFalse(json.loads(rejected.stdout)["matched"])
        self.assertEqual(self.snapshot(), before)
        self.cp = self.c.repair_reciprocity(self.tid, self.cp.version)
        before = self.snapshot()
        result = subprocess.run([sys.executable, "-c", script, str(self.path), json.dumps(self.fixture), self.tid],
                                capture_output=True, text=True, check=True, timeout=15, env=child_env)
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt["matched"])
        self.assertEqual(receipt["reciprocal_readback"]["connection"]["connection_id"], self.tid + ":connection")
        self.assertEqual(receipt["reciprocal_readback"]["connection"]["version"], 2)
        self.assertEqual(len(receipt["reciprocal_readback"]["endpoint_references"]), 2)
        self.assertTrue(receipt["reader_identity"].startswith("synthetic:reader:"))
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.c.resume(self.tid, self.cp.version).disposition, "VERIFIED")
