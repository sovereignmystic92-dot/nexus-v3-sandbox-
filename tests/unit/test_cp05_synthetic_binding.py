"""CP05 bounded synthetic binding regressions; NOT provider or host assurance."""
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from nexus_sandbox.authority import default_records
from nexus_sandbox.contracts import Request
from nexus_sandbox.coordinator import SQLiteCoordinator, BindingConflict, digest


class CP05SyntheticBindingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="cp05-binding-")
        self.addCleanup(tmp.cleanup)
        self.db = Path(tmp.name) / "cp05.sqlite"
        self.fixture = json.loads((Path(__file__).parents[1] / "fixtures/complete-source.json").read_text())
        f = self.fixture
        self.request = Request(f["idempotency_key"], f["source_id"], f["source_revision"],
                               f["destination_id"], digest(f["payload"]), True)

    def worker(self, authority=None):
        return SQLiteCoordinator(self.db, [self.fixture], authority_records=authority,
                                 case_id="CP05-SYNTHETIC",
                                 runtime_identity="synthetic:runtime:cp05-regression")

    def rows(self):
        with sqlite3.connect(self.db) as db:
            return {t: db.execute("SELECT * FROM " + t + " ORDER BY rowid").fetchall()
                    for t in ("transactions", "artifacts", "events", "attempts")}

    def test_valid_fixture_completes_with_bound_output(self):
        worker = self.worker()
        cp = worker.submit(self.request)
        for _ in range(5):
            cp = worker.resume(cp.transaction_id, cp.version)
        self.assertEqual((cp.state, cp.disposition), ("VERIFIED", "VERIFIED"))
        with sqlite3.connect(self.db) as reader:
            rows = reader.execute("SELECT kind,destination_id,payload_sha256 FROM artifacts").fetchall()
        self.assertEqual({(kind, destination) for kind, destination, _ in rows},
                         {("archive", "synthetic:archive"), ("output", "synthetic:output"),
                          ("registry", "synthetic:output")})
        self.assertTrue(all(sha == digest(self.fixture["payload"]) for _, _, sha in rows))

    def test_wrong_destination_denied_before_any_state_change(self):
        worker = self.worker()
        before = self.rows()
        with self.assertRaises(ValueError):
            worker.submit(replace(self.request, destination_id="synthetic:archive"))
        self.assertEqual(self.rows(), before)

    def test_reused_key_conflicting_source_binding_denied_without_mutation(self):
        worker = self.worker()
        worker.submit(self.request)
        before = self.rows()
        with self.assertRaises(BindingConflict):
            worker.submit(replace(self.request, source_revision="wrong"))
        self.assertEqual(self.rows(), before)

    def test_denied_authority_never_creates_artifacts(self):
        denied = default_records() + [dict(default_records()[0],
            document_id="synthetic:authority:cp05-denial", rule="deny_synthetic_output")]
        worker = self.worker(denied)
        cp = worker.submit(self.request)
        self.assertEqual(cp.disposition, "BLOCKED")
        self.assertEqual(self.rows()["artifacts"], [])
        self.assertEqual(worker.resume(cp.transaction_id, cp.version), cp)
        self.assertEqual(self.rows()["artifacts"], [])
