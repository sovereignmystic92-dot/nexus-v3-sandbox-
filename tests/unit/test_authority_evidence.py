"""Authority and evidence acceptance components in a local test harness."""

from dataclasses import replace
import json
import sqlite3
import unittest

from nexus_sandbox.authority import default_records, resolve
from nexus_sandbox.coordinator import SQLiteCoordinator
import test_coordinator as support


class AuthorityEvidenceTests(unittest.TestCase):
    setUp = support.CoordinatorTests.setUp
    sql = support.CoordinatorTests.sql
    run_to = support.CoordinatorTests.run_to

    def with_authority(self, records):
        return SQLiteCoordinator(self.path, [self.fixture], authority_records=records,
                                 case_id=self.id(), runtime_identity="synthetic:runtime:unit-tests")

    def envelopes(self):
        return [json.loads(r[0]) for r in self.sql("SELECT envelope_json FROM attempts ORDER BY rowid")]

    def test_s06_historical_source_and_hypothesis_do_not_govern(self):
        records = default_records()
        for role in ("historical", "source", "hypothesis"):
            records.append({"document_id": "synthetic:authority:" + role, "revision": "1",
                            "role": role, "rule": "deny_synthetic_output"})
        self.coordinator = self.with_authority(records)
        cp = self.run_to()
        self.assertEqual(cp.state, "VERIFIED")
        evidence = self.envelopes()[-1]
        self.assertEqual({d["role"] for d in evidence["authority_provenance"]},
                         {"current", "historical", "source", "hypothesis"})

    def test_conflicting_current_authority_blocks_without_artifacts(self):
        records = default_records() + [{"document_id": "synthetic:authority:conflict", "revision": "1",
                                        "role": "current", "rule": "deny_synthetic_output"}]
        self.coordinator = self.with_authority(records)
        cp = self.coordinator.submit(self.request)
        self.assertEqual((cp.state, cp.disposition), ("NEW", "BLOCKED"))
        self.assertEqual(self.sql("SELECT count(*) FROM artifacts"), [(0,)])
        self.assertIn("conflicting current authority", self.envelopes()[-1]["observed_result"])

    def test_absent_or_denied_current_authority_fails_closed(self):
        for records in ([], [dict(default_records()[0], rule="deny_synthetic_output")]):
            self.assertFalse(resolve(records).allowed)
        self.coordinator = self.with_authority([])
        cp = self.coordinator.submit(self.request)
        self.assertEqual(cp.disposition, "BLOCKED")
        self.assertEqual(self.sql("SELECT count(*) FROM artifacts"), [(0,)])

    def test_malformed_or_duplicate_authority_rejected(self):
        original = default_records()[0]
        for records in ([original, original], [dict(original, role="system")],
                        [dict(original, rule="allow_production")], [dict(original, revision="")]):
            with self.subTest(records=records), self.assertRaises(ValueError):
                self.with_authority(records)

    def test_changed_authority_holds_checkpoint_then_bound_policy_can_resume(self):
        cp = self.run_to("ARCHIVED")
        before = self.sql("SELECT * FROM artifacts")
        self.coordinator = self.with_authority([dict(default_records()[0], revision="2")])
        held = self.coordinator.resume(cp.transaction_id, cp.version)
        self.assertEqual((held.state, held.disposition), ("ARCHIVED", "BLOCKED"))
        self.assertEqual(self.sql("SELECT * FROM artifacts"), before)
        self.coordinator = self.with_authority(default_records())
        resumed = self.coordinator.resume(held.transaction_id, held.version)
        self.assertEqual((resumed.state, resumed.disposition), ("OUTPUT_CREATED", "OPEN"))

    def test_authority_order_does_not_change_governing_revision(self):
        records = default_records() + [dict(default_records()[0], document_id="synthetic:authority:second")]
        self.assertEqual(resolve(records).governing_revision, resolve(list(reversed(records))).governing_revision)
        self.assertTrue(resolve(records).allowed)

    def test_full_envelope_fields_and_independent_readback_hashes(self):
        self.coordinator = self.with_authority(default_records())
        cp = self.run_to()
        required = set("schema_version run_id case_id attempt_id fixture_revision code_revision runtime_identity started_at_utc ended_at_utc expected_result observed_result operation_outcome protocol_verdict last_confirmed_state next_action artifact_ids expected_hashes readback_hashes reader_identity evidence_refs limitations".split())
        envelopes = self.envelopes()
        self.assertEqual(len(envelopes), 6)
        self.assertEqual(len({e["attempt_id"] for e in envelopes}), 6)
        for envelope in envelopes:
            self.assertFalse(required - envelope.keys())
            self.assertLessEqual(envelope["started_at_utc"], envelope["ended_at_utc"])
            self.assertTrue(envelope["code_revision"].startswith("sha256:"))
        final = envelopes[-1]
        self.assertEqual(final["protocol_verdict"], "VERIFIED")
        self.assertEqual(final["expected_hashes"], final["readback_hashes"])
        self.assertEqual(final["last_confirmed_state"], cp.state)
        self.assertTrue(final["reader_identity"].startswith("synthetic:reader:"))
        event_refs = {r[0] for r in self.sql("SELECT evidence_ref FROM events")}
        self.assertEqual(event_refs, {e["attempt_id"] for e in envelopes})

    def test_blocked_attempt_reports_not_attempted_and_preserves_provenance(self):
        self.coordinator = self.with_authority([])
        self.coordinator.submit(self.request)
        e = self.envelopes()[-1]
        self.assertEqual((e["operation_outcome"], e["protocol_verdict"]), ("NOT_ATTEMPTED", "BLOCKED"))
        self.assertEqual(e["readback_hashes"], {})
        self.assertIsNone(e["reader_identity"])

    def test_failed_readback_preserves_failed_attempt_after_repair(self):
        cp = self.run_to("REGISTERED")
        self.sql("UPDATE artifacts SET payload='tampered' WHERE kind='output'")
        cp = self.coordinator.resume(cp.transaction_id, cp.version)
        failure = self.envelopes()[-1]
        self.assertEqual((failure["operation_outcome"], failure["protocol_verdict"]), ("FAILED", "FAILED"))
        self.assertNotEqual(failure["expected_hashes"], failure["readback_hashes"])
        self.sql("UPDATE artifacts SET payload=? WHERE kind='output'", (self.fixture["payload"],))
        self.coordinator.resume(cp.transaction_id, cp.version)
        self.assertEqual(self.envelopes()[-2], failure)
        self.assertEqual(self.envelopes()[-1]["protocol_verdict"], "VERIFIED")

    def test_failed_event_write_rolls_back_attempt_and_verification(self):
        cp = self.run_to("REGISTERED")
        before = self.envelopes()
        self.sql("CREATE TRIGGER deny_event BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.coordinator.resume(cp.transaction_id, cp.version)
        self.assertEqual(self.envelopes(), before)
        self.assertEqual(self.coordinator.submit(self.request), cp)


if __name__ == "__main__":
    unittest.main()
