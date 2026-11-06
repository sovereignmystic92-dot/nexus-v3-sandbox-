"""Risk-gated, durable intent preparation; NO order submission.

Preflight approval is not a broker authorization. Every invocation requires
a freshly verified snapshot. Durable reservation is represented by RESERVED,
but account-wide exposure reservation/reconciliation remains future work.
"""
from dataclasses import asdict
from decimal import Decimal
from tools.trader_paper_risk import authorize, RiskRejected
from tools.trader_paper_journal import JournalConflict

def prepare_paper_intent(journal, client_order_id, snapshot, *, symbol, side="buy"):
    """Fail closed on any unresolved prior order; journal preflight before reserve.

    Returns a durable reservation ID for a future, separately approved executor.
    Never calls a broker. Caller must reconcile pending reservations against
    current broker state before any subsequent proposal.
    """
    if journal.unresolved():
        raise JournalConflict("unresolved reservations require reconciliation")
    if not isinstance(symbol, str) or not symbol.strip() or side != "buy":
        raise RiskRejected("only explicit long equity buys permitted")
    result = authorize(snapshot)
    payload = {
        "symbol": symbol.strip().upper(), "side": side,
        "planned_loss": str(snapshot.planned_loss),
        "proposed_buy_notional": str(snapshot.proposed_buy_notional),
        "legacy_market_value": str(snapshot.legacy_market_value),
        "other_position_market_value": str(snapshot.other_position_market_value),
        "pending_buy_notional": str(snapshot.pending_buy_notional),
        "daily_loss": str(snapshot.daily_loss),
        "remaining_exposure": result["remaining_exposure"],
        "paper_only": True,
        "execution_enabled": False,
    }
    created = journal.prepare(client_order_id, payload)
    if not created:
        raise JournalConflict("duplicate intent; never reserve or retry")
    journal.transition(client_order_id, "PREPARED", "RESERVED",
                       detail="risk preflight passed; no broker submission")
    return {"client_order_id": client_order_id, "state": "RESERVED",
            "execution_enabled": False}
