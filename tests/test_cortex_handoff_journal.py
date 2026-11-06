import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from nexus_sandbox.cortex_handoff_journal import (
    HandoffJournal, Intent, JournalHold, analysis_hash,
)


def fixture():
    return Intent("haiti-1", "https://app.notion.com/p/source",
                  "https://app.notion.com/p/analysis", "rev-1", "rev-2",
                  "account", "owner", analysis_hash("derived analysis"))


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "journal.sqlite"
        self.journal = HandoffJournal(self.path)
        self.intent = fixture()

    def test_reopen_retains_write_intent_and_refuses_retry(self):
        self.assertEqual(self.journal.begin(self.intent), ("PREPARED", None))
        self.journal.mark_write_intent(self.intent)
        restarted = HandoffJournal(self.path)
        self.assertEqual(restarted.begin(self.intent), ("WRITE_INTENT", None))
        with self.assertRaises(JournalHold):
            restarted.mark_write_intent(self.intent)

    def test_conflicting_binding_is_blocked(self):
        self.journal.begin(self.intent)
        with self.assertRaises(JournalHold):
            self.journal.begin(replace(self.intent, destination_owner="other"))

    def test_verified_identity_survives_restart(self):
        self.journal.begin(self.intent)
        self.journal.mark_write_intent(self.intent)
        self.journal.reconcile_verified(self.intent, "module-1")
        self.assertEqual(HandoffJournal(self.path).begin(self.intent),
                         ("VERIFIED", "module-1"))
        with self.assertRaises(JournalHold):
            self.journal.reconcile_verified(self.intent, "module-2")

    def test_cannot_verify_without_intent(self):
        self.journal.begin(self.intent)
        with self.assertRaises(JournalHold):
            self.journal.reconcile_verified(self.intent, "module-1")

    def test_empty_analysis_rejected(self):
        with self.assertRaises(JournalHold):
            analysis_hash("  ")


if __name__ == "__main__":
    unittest.main()
