"""Offline checks only: no broker calls."""
import unittest
from dataclasses import replace
from decimal import Decimal
from tools.trader_paper_risk import Snapshot, RiskRejected, authorize

BASE = Snapshot(
    legacy_market_value="56.56539", other_position_market_value="0",
    pending_buy_notional="0", proposed_buy_notional="43.43",
    planned_loss="1", daily_loss="0", open_position_count=1,
    account_verified=True, positions_verified=True, orders_verified=True,
    quotes_fresh=True, journal_prepared=True, unique_order_id=True,
    paper_endpoint=True, long_only_equity=True, no_margin=True,
    kill_switch_clear=True)

class PilotRiskTests(unittest.TestCase):
    def test_boundary_pass(self):
        self.assertEqual(authorize(BASE)["remaining_exposure"], "0.00461")

    def reject(self, **changes):
        with self.assertRaises(RiskRejected):
            authorize(replace(BASE, **changes))

    def test_exposure(self):
        self.reject(proposed_buy_notional="43.44")
        self.reject(pending_buy_notional="0.01")
        self.reject(other_position_market_value="0.01")
        self.reject(legacy_market_value="57")

    def test_risk_and_daily_stop(self):
        self.reject(planned_loss="1.01")
        self.reject(daily_loss="3")
        self.reject(daily_loss="4")

    def test_fail_closed(self):
        for key in ("account_verified", "positions_verified", "orders_verified",
                    "quotes_fresh", "journal_prepared", "unique_order_id",
                    "paper_endpoint", "long_only_equity", "no_margin",
                    "kill_switch_clear"):
            with self.subTest(key=key):
                self.reject(**{key: False})
        self.reject(open_position_count=3)
        self.reject(open_position_count=True)
        self.reject(proposed_buy_notional="NaN")
        self.reject(proposed_buy_notional="-1")
        self.reject(proposed_buy_notional="0")
        self.reject(daily_loss="Infinity")

if __name__ == "__main__":
    unittest.main()
