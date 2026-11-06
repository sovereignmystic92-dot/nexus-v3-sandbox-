"""Read-only normalization of Alpaca account/positions/orders payloads.

This adapter accepts caller-supplied broker API responses. It never calls a broker,
submits orders, or assumes that a chat plugin connection exists in GitHub Actions.
"""
from decimal import Decimal
from tools.trader_paper_risk import Snapshot, RiskRejected, money

def snapshot_from_alpaca(account, positions, orders, *, proposed_buy_notional,
                         planned_loss, daily_loss, quotes_fresh=False,
                         journal_prepared=False, unique_order_id=False,
                         paper_endpoint=False, no_margin=False,
                         kill_switch_clear=False):
    if not isinstance(account, dict) or account.get("status") != "ACTIVE":
        raise RiskRejected("account not verified active")
    if not isinstance(positions, list) or not isinstance(orders, list):
        raise RiskRejected("positions or orders not verified")
    if account.get("trading_blocked") is not False:
        raise RiskRejected("broker account blocked or unknown")
    legacy = Decimal("0")
    other = Decimal("0")
    for p in positions:
        if not isinstance(p, dict) or p.get("side") != "long" or p.get("asset_class") != "us_equity":
            raise RiskRejected("unsupported position")
        value = money(p.get("market_value"))
        if p.get("symbol") == "IOVA":
            legacy += value
        else:
            other += value
    pending = Decimal("0")
    for o in orders:
        if not isinstance(o, dict):
            raise RiskRejected("invalid order")
        if o.get("status") not in ("new", "accepted", "pending_new", "partially_filled", "held", "accepted_for_bidding", "calculated"):
            raise RiskRejected("unexpected open-order status")
        if o.get("side") != "buy":
            raise RiskRejected("unreconciled non-buy open order")
        notional = o.get("notional")
        if notional is None:
            # Quantity orders require a fresh, externally verified price to reserve.
            raise RiskRejected("open order lacks verifiable notional")
        pending += money(notional)
    return Snapshot(
        legacy_market_value=legacy, other_position_market_value=other,
        pending_buy_notional=pending, proposed_buy_notional=proposed_buy_notional,
        planned_loss=planned_loss, daily_loss=daily_loss,
        open_position_count=len(positions),
        account_verified=True, positions_verified=True, orders_verified=True,
        quotes_fresh=quotes_fresh, journal_prepared=journal_prepared,
        unique_order_id=unique_order_id, paper_endpoint=paper_endpoint,
        long_only_equity=True, no_margin=no_margin,
        kill_switch_clear=kill_switch_clear)
