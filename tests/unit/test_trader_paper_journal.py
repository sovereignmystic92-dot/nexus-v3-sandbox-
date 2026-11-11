"""Offline durability and duplicate intent tests; no Alpaca execution."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import tempfile
import unittest
from tools.trader_paper_journal import PaperJournal, JournalConflict

class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "paper.sqlite"
        self.journal = PaperJournal(self.path)

    def test_restart_preserves_state_and_prevents_duplicate(self):
        self.assertTrue(self.journal.prepare("pilot-001", {"symbol":"SPY","side":"buy"}))
        self.assertFalse(self.journal.prepare("pilot-001", {"symbol":"SPY","side":"buy"}))
        self.journal.transition("pilot-001", "PREPARED", "RESERVED")
        restarted = PaperJournal(self.path)
        self.assertEqual(restarted.state("pilot-001"), "RESERVED")
        self.assertEqual(restarted.unresolved(), [("pilot-001", "RESERVED")])
        with self.assertRaises(JournalConflict):
            restarted.transition("pilot-001", "PREPARED", "RESERVED")

    def test_reused_id_with_different_intent_rejected(self):
        self.journal.prepare("pilot-002", {"symbol":"SPY"})
        with self.assertRaises(JournalConflict):
            self.journal.prepare("pilot-002", {"symbol":"IOVA"})

    def test_uncertain_requires_explicit_reconciliation(self):
        self.journal.prepare("pilot-003", {"symbol":"SPY"})
        self.journal.transition("pilot-003", "PREPARED", "RESERVED")
        self.journal.transition("pilot-003", "RESERVED", "UNCERTAIN")
        self.assertEqual(PaperJournal(self.path).unresolved(), [("pilot-003","UNCERTAIN")])
        with self.assertRaises(JournalConflict):
            self.journal.transition("pilot-003", "UNCERTAIN", "RESERVED")
        self.journal.transition("pilot-003", "UNCERTAIN", "RECONCILED",
                                detail="verified via independent broker lookup",
                                broker_order_id="paper-example")
        self.assertEqual(self.journal.unresolved(), [])

    def test_missing_id_and_invalid_transition(self):
        with self.assertRaises(JournalConflict):
            self.journal.prepare("", {"symbol":"SPY"})
        with self.assertRaises(JournalConflict):
            self.journal.transition("missing", "PREPARED", "RESERVED")

if __name__ == "__main__":
    unittest.main()
