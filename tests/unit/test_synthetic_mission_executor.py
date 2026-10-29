"""Local synthetic step effects only: no external dispatch or live credentials."""
from pathlib import Path
import tempfile
import unittest

from nexus_sandbox.mission_dispatcher import Mission
from nexus_sandbox.mission_journal import MissionJournal
from nexus_sandbox.synthetic_mission_executor import (
    advance_synthetic, _receipt_path, _receipt_bytes, _check_receipt,
)


class SyntheticMissionExecutorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.journal = MissionJournal.provision(self.folder / "mission.sqlite", "sandbox-only")
        self.mission = Mission("mission-1", "PASSIVE", "synthetic-trigger",
                               ("source-checked",), ("inspect", "review"))
        self.defaults = dict(observed_triggers=("synthetic-trigger",),
                             satisfied_dependencies=("source-checked",))

    def advance(self, **kwargs):
        opts = dict(self.defaults)
        opts.update(kwargs)
        return advance_synthetic(self.journal, self.mission, self.folder, **opts)

    def test_one_step_per_call_and_verified_completion(self):
        first = self.advance()
        self.assertEqual(first["revision"], 1)
        self.assertEqual(first["evidence"]["verified"], ["inspect"])
        second = self.advance(expected_revision=1)
        self.assertEqual(second["evidence"]["verified"], ["inspect", "review"])
        last = self.advance(expected_revision=2)
        self.assertEqual(last["decision"]["state"], "COMPLETE")
        self.assertEqual(last["revision"], 2)
        self.assertEqual(len(list(self.folder.glob("*.receipt"))), 2)

    def test_interrupted_after_effect_reconciles_without_second_write(self):
        with self.assertRaises(InterruptedError):
            self.advance(after_fixture_write="INTERRUPT")
        self.assertIsNone(self.journal.observe(self.mission.mission_id))
        receipts = list(self.folder.glob("*.receipt"))
        self.assertEqual(len(receipts), 1)
        first_bytes = receipts[0].read_bytes()
        recovered = self.advance()
        self.assertEqual(recovered["evidence"]["verified"], ["inspect"])
        self.assertEqual(receipts[0].read_bytes(), first_bytes)
        self.assertEqual(len(list(self.folder.glob("*.receipt"))), 1)

    def test_missing_trigger_never_executes(self):
        result = self.advance(observed_triggers=())
        self.assertEqual(result["decision"]["state"], "HOLD")
        self.assertEqual(list(self.folder.glob("*.receipt")), [])

    def test_missing_dependency_never_executes(self):
        result = self.advance(satisfied_dependencies=())
        self.assertEqual(result["decision"]["reason"], "DEPENDENCIES_UNMET")
        self.assertEqual(list(self.folder.glob("*.receipt")), [])

    def test_stale_revision_cannot_execute_new_step(self):
        self.advance()
        with self.assertRaises(ValueError):
            self.advance(expected_revision=0)
        self.assertEqual(len(list(self.folder.glob("*.receipt"))), 1)

    def test_conflicting_receipt_fails_closed(self):
        contract = self.advance()["decision"]["contract_digest"]
        target = _receipt_path(self.folder, self.mission.mission_id, contract, "review")
        target.write_bytes(b"conflict")
        target.chmod(0o600)
        with self.assertRaises(ValueError):
            self.advance(expected_revision=1)
        self.assertEqual(self.journal.observe(self.mission.mission_id)["revision"], 1)

    def test_active_execution_refused(self):
        self.mission = Mission("mission-active", "ACTIVE", "synthetic-trigger", (),
                               ("inspect",))
        with self.assertRaises(ValueError):
            self.advance()

    def test_missing_journal_fails_without_replacement(self):
        self.journal.path.unlink()
        with self.assertRaises(FileNotFoundError):
            self.advance()
        self.assertFalse(self.journal.path.exists())

    def test_invalid_receipt_is_not_treated_as_absent(self):
        self.advance()
        receipt = next(self.folder.glob("*.receipt"))
        receipt.chmod(0o644)
        with self.assertRaises(ValueError):
            _check_receipt(receipt, receipt.read_bytes())


if __name__ == "__main__":
    unittest.main()
