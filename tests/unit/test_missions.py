"""Whole synthetic transaction missions; no external knowledge processing."""

from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from nexus_sandbox.authority import default_records
from nexus_sandbox.contracts import Request
from nexus_sandbox.coordinator import SQLiteCoordinator, digest


class MissionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="nexus-mission-")
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "mission.sqlite"
        self.fixture = json.loads((Path(__file__).parents[1] / "fixtures/complete-source.json").read_text())
        f = self.fixture
        self.request = Request(f["idempotency_key"], f["source_id"], f["source_revision"],
                               f["destination_id"], digest(f["payload"]), True)

    def coordinator(self, case, authority=None):
        return SQLiteCoordinator(self.path, [self.fixture], case_id=case,
                                 authority_records=authority,
                                 runtime_identity="synthetic:runtime:mission-suite")

    def snapshot(self):
        with closing(sqlite3.connect(self.path)) as reader:
            return {table: reader.execute("SELECT * FROM " + table + " ORDER BY rowid").fetchall()
                    for table in ("transactions", "artifacts", "events", "attempts")}

    def finish(self, worker, cp):
        for _ in range(5):
            if cp.state == "VERIFIED":
                break
            cp = worker.resume(cp.transaction_id, cp.version)
        self.assertEqual((cp.state, cp.disposition), ("VERIFIED", "VERIFIED"))
        return cp

    def assert_complete_trace(self, cp, case):
        snap = self.snapshot()
        self.assertEqual(len(snap["transactions"]), 1)
        artifacts = {row[2]: row for row in snap["artifacts"]}
        self.assertEqual(set(artifacts), {"archive", "output", "registry"})
        for kind, row in artifacts.items():
            self.assertEqual(row, (cp.transaction_id + ":" + kind, cp.transaction_id, kind,
                             "synthetic:archive" if kind == "archive" else "synthetic:output",
                             self.fixture["payload"], digest(self.fixture["payload"])))
        events = snap["events"]
        states = ["NEW", "VALIDATED", "ARCHIVED", "OUTPUT_CREATED", "REGISTERED", "VERIFIED"]
        self.assertEqual([e[3] for e in events], states)
        self.assertEqual([e[2] for e in events], [None] + states[:-1])
        attempts = {r[0]: json.loads(r[2]) for r in snap["attempts"]}
        self.assertEqual(len(attempts), 6)
        self.assertEqual({e[5] for e in events}, set(attempts))
        for event in events:
            envelope = attempts[event[5]]
            self.assertEqual(envelope["case_id"], case)
            self.assertEqual(envelope["transaction_id"], cp.transaction_id)
            self.assertEqual(envelope["last_confirmed_state"], event[3])
        final = attempts[events[-1][5]]
        self.assertEqual(final["protocol_verdict"], "VERIFIED")
        self.assertEqual(final["expected_hashes"], final["readback_hashes"])
        self.assertTrue(final["reader_identity"].startswith("synthetic:reader:"))
        self.assertIsNotNone(final["readback_observed_at_utc"])

    def test_m01_complete_mission_and_repeat_are_durable(self):
        worker = self.coordinator("M01")
        cp = self.finish(worker, worker.submit(self.request))
        self.assert_complete_trace(cp, "M01")
        before = self.snapshot()
        reopened = self.coordinator("M01")
        self.assertEqual(reopened.submit(self.request), cp)
        self.assertEqual(reopened.resume(cp.transaction_id, cp.version), cp)
        self.assertEqual(self.snapshot(), before)

    def test_m02_interrupted_mission_resumes_without_duplicate_work(self):
        worker = self.coordinator("M02")
        cp = worker.submit(self.request)
        for _ in range(3):
            cp = worker.resume(cp.transaction_id, cp.version)
        self.assertEqual(cp.state, "OUTPUT_CREATED")
        before = self.snapshot()
        del worker
        reopened = self.coordinator("M02")
        self.assertEqual(reopened.submit(self.request), cp)
        self.assertEqual(self.snapshot(), before)
        cp = self.finish(reopened, cp)
        self.assert_complete_trace(cp, "M02")
        self.assertTrue(set(before["artifacts"]).issubset(set(self.snapshot()["artifacts"])))

    def assert_held(self, worker, request, case):
        cp = worker.submit(request)
        self.assertEqual((cp.state, cp.disposition), ("NEW", "BLOCKED"))
        before = self.snapshot()
        self.assertEqual(before["artifacts"], [])
        self.assertEqual(worker.resume(cp.transaction_id, cp.version), cp)
        self.assertEqual(worker.submit(request), cp)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(before["events"]), 1)
        self.assertEqual(len(before["attempts"]), 1)
        envelope = json.loads(before["attempts"][0][2])
        self.assertEqual(envelope["case_id"], case)
        self.assertEqual((envelope["operation_outcome"], envelope["protocol_verdict"]),
                         ("NOT_ATTEMPTED", "BLOCKED"))
        self.assertIsNone(envelope["reader_identity"])
        self.assertEqual(envelope["readback_hashes"], {})
        self.assertNotEqual(cp.next_action, "none")

    def test_m03_incomplete_evidence_holds_whole_mission(self):
        self.fixture["source_complete"] = False
        self.assert_held(self.coordinator("M03"), replace(self.request, source_complete=False), "M03")

    def test_m04_current_authority_conflict_holds_whole_mission(self):
        authority = default_records() + [dict(default_records()[0],
            document_id="synthetic:authority:mission-conflict", rule="deny_synthetic_output")]
        self.assert_held(self.coordinator("M04", authority), self.request, "M04")
