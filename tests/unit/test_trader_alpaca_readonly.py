"""Offline tests of the read-only broker payload adapter."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import unittest
from tools.trader_alpaca_readonly import snapshot_from_alpaca
from tools.trader_paper_risk import authorize, RiskRejected

ACCOUNT = {"status":"ACTIVE","trading_blocked":False}
POSITIONS = [{"symbol":"IOVA","side":"long","asset_class":"us_equity","market_value":"56.56539"}]
FLAGS = dict(proposed_buy_notional="43.43",planned_loss="1",daily_loss="0",
             quotes_fresh=True,journal_prepared=True,unique_order_id=True,
             paper_endpoint=True,no_margin=True,kill_switch_clear=True)

class ReadOnlyAdapterTests(unittest.TestCase):
    def test_existing_iova_and_empty_orders(self):
        snapshot = snapshot_from_alpaca(ACCOUNT, POSITIONS, [], **FLAGS)
        self.assertEqual(authorize(snapshot)["remaining_exposure"], "0.00461")

    def test_pending_buy_blocks_exposure(self):
        orders = [{"status":"new","side":"buy","notional":"0.01"}]
        with self.assertRaises(RiskRejected):
            authorize(snapshot_from_alpaca(ACCOUNT, POSITIONS, orders, **FLAGS))

    def test_qty_order_without_price_fails_closed(self):
        with self.assertRaises(RiskRejected):
            snapshot_from_alpaca(ACCOUNT, POSITIONS, [{"status":"new","side":"buy","qty":"1"}], **FLAGS)

    def test_unverified_broker_conditions_reject(self):
        with self.assertRaises(RiskRejected):
            snapshot_from_alpaca({"status":"ACTIVE"}, POSITIONS, [], **FLAGS)
        with self.assertRaises(RiskRejected):
            snapshot_from_alpaca(ACCOUNT, None, [], **FLAGS)
        with self.assertRaises(RiskRejected):
            authorize(snapshot_from_alpaca(ACCOUNT, POSITIONS, [], **(FLAGS | {"paper_endpoint":False})))

if __name__ == "__main__":
    unittest.main()
