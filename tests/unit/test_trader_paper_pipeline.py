"""Offline integration tests for risk -> journal; no order execution."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import tempfile
import unittest
from dataclasses import replace
from tools.trader_paper_risk import Snapshot, RiskRejected
from tools.trader_paper_journal import PaperJournal, JournalConflict
from tools.trader_paper_pipeline import prepare_paper_intent

BASE = Snapshot(
    legacy_market_value="56.56539", other_position_market_value="0",
    pending_buy_notional="0", proposed_buy_notional="43.43",
    planned_loss="1", daily_loss="0", open_position_count=1,
    account_verified=True, positions_verified=True, orders_verified=True,
    quotes_fresh=True, journal_prepared=True, unique_order_id=True,
    paper_endpoint=True, long_only_equity=True, no_margin=True,
    kill_switch_clear=True)

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "pilot.sqlite"
        self.journal = PaperJournal(self.path)

    def test_risk_pass_creates_durable_reservation(self):
        result = prepare_paper_intent(self.journal, "pilot-1", BASE, symbol="SPY")
        self.assertEqual(result["state"], "RESERVED")
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(PaperJournal(self.path).state("pilot-1"), "RESERVED")

    def test_over_budget_never_journaled(self):
        with self.assertRaises(RiskRejected):
            prepare_paper_intent(self.journal, "pilot-2",
                replace(BASE, proposed_buy_notional="43.44"), symbol="SPY")
        self.assertIsNone(self.journal.state("pilot-2"))

    def test_restart_blocks_duplicate_and_new_orders(self):
        prepare_paper_intent(self.journal, "pilot-3", BASE, symbol="SPY")
        restarted = PaperJournal(self.path)
        with self.assertRaises(JournalConflict):
            prepare_paper_intent(restarted, "pilot-3", BASE, symbol="SPY")
        with self.assertRaises(JournalConflict):
            prepare_paper_intent(restarted, "pilot-4", BASE, symbol="SPY")
        self.assertIsNone(restarted.state("pilot-4"))

    def test_missing_verification_never_journaled(self):
        with self.assertRaises(RiskRejected):
            prepare_paper_intent(self.journal, "pilot-5",
                replace(BASE, orders_verified=False), symbol="SPY")
        self.assertIsNone(self.journal.state("pilot-5"))

if __name__ == "__main__":
    unittest.main()
