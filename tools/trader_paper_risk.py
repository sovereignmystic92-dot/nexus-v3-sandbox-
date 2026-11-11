"""Pure, fail-closed paper pilot risk checks. No brokerage connectivity or orders."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

BUDGET = Decimal("100")
MAX_PLANNED_RISK = Decimal("1")
DAILY_STOP = Decimal("3")
MAX_POSITIONS = 3

class RiskRejected(ValueError):
    pass

def money(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise RiskRejected("invalid numeric input") from None
    if not amount.is_finite() or amount < 0:
        raise RiskRejected("invalid numeric input")
    return amount

@dataclass(frozen=True)
class Snapshot:
    legacy_market_value: object
    other_position_market_value: object
    pending_buy_notional: object
    proposed_buy_notional: object
    planned_loss: object
    daily_loss: object
    open_position_count: int
    account_verified: bool
    positions_verified: bool
    orders_verified: bool
    quotes_fresh: bool
    journal_prepared: bool
    unique_order_id: bool
    paper_endpoint: bool
    long_only_equity: bool
    no_margin: bool
    kill_switch_clear: bool

def authorize(snapshot: Snapshot) -> dict:
    """Validate one proposed new paper BUY; caller must atomically reserve before any submit.

    No external writes occur here. Approval is only a numerical/preflight result,
    never brokerage order authorization.
    """
    flags = (snapshot.account_verified, snapshot.positions_verified,
             snapshot.orders_verified, snapshot.quotes_fresh,
             snapshot.journal_prepared, snapshot.unique_order_id,
             snapshot.paper_endpoint, snapshot.long_only_equity,
             snapshot.no_margin, snapshot.kill_switch_clear)
    if not all(flag is True for flag in flags):
        raise RiskRejected("missing verification or prohibited trading mode")
    if type(snapshot.open_position_count) is not int or not 0 <= snapshot.open_position_count < MAX_POSITIONS:
        raise RiskRejected("position limit or invalid count")
    legacy = money(snapshot.legacy_market_value)
    other = money(snapshot.other_position_market_value)
    pending = money(snapshot.pending_buy_notional)
    proposed = money(snapshot.proposed_buy_notional)
    planned_loss = money(snapshot.planned_loss)
    daily_loss = money(snapshot.daily_loss)
    if proposed <= 0:
        raise RiskRejected("order must have positive notional")
    if planned_loss > MAX_PLANNED_RISK:
        raise RiskRejected("per-trade planned loss exceeds $1")
    if daily_loss >= DAILY_STOP:
        raise RiskRejected("daily loss shutdown threshold reached")
    exposure = legacy + other + pending + proposed
    if exposure > BUDGET:
        raise RiskRejected("aggregate exposure exceeds $100")
    return {"preflight_only": True, "remaining_exposure": str(BUDGET - exposure)}
