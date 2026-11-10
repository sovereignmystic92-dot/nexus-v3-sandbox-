# Nexus Trading Platform v0.1 — implementation contract

Status: design scaffold only. No broker connections, orders, or unattended trading enabled.

## Scope
Support US stocks/ETFs and cryptocurrency through separate market adapters with a shared, auditable decision pipeline. Initial phase is simulated/paper trading only. A $100 reference budget is a risk-design constraint, not permission to fund an account or trade.

## Pipeline
1. Acquire timestamped, source-attributed market data; validate symbol, venue, currency, freshness, and corporate actions where applicable.
2. Generate strategy signals with explicit model/strategy version and supporting evidence.
3. Backtest without look-ahead bias, including transaction costs, spread, slippage, and out-of-sample evaluation.
4. Apply deterministic pre-trade risk policy independently of AI-generated signals.
5. Route eligible simulated orders to paper-only adapters; persist request, response, fill, rejection, and reconciliation evidence.
6. Perform independent readback, post-trade evaluation, and append-only audit logging.

## Market differences
- Equities/ETFs: exchange calendars, trading halts, fractional-share support, settlement, corporate actions, market/extended-hours policies.
- Crypto: 24/7 markets, exchange outages, venue-specific precision/minimums, custody and volatility controls.
- Common: symbol normalization, data provenance, order idempotency, position and exposure limits, fee-aware P&L, kill switch.

## Safety and acceptance gates
- No live order submission, credential provisioning, or account funding in v0.1.
- Explicit environment separation: backtest / paper / live. Live is disabled by default and cannot be activated by a model-generated signal.
- No AI override of deterministic risk checks; fail closed on missing/stale data, missing permissions, unreconciled positions, or unavailable broker.
- Initial reference capital: $100; enforce configurable per-order, daily-loss, concentration, and exposure caps in tests before paper execution. Values require owner approval.
- Secrets never committed. Every execution attempt must be idempotent and independently reconciled.
- Synthetic unit tests, backtest integrity tests, fault injection, paper-broker tests, independent reviewer evidence, and owner sign-off required before any proposal to enable live trading.

## Initial work items
1. Inventory existing Nexus modules, workflows, and constitutional controls.
2. Define market-data, strategy-signal, risk-decision, and order-event schemas.
3. Implement deterministic paper-only engine and fixtures for equities and crypto.
4. Add reproducible offline test suite and CI enforcement.
5. Integrate Cortex derived outputs and Notion source/evidence records only after connector permission and readback verification.
6. Invite Gemini for bounded independent review when a verified bridge is available.

Owner-facing controller: ChatGPT. Code enforcement: GitHub Actions. Gemini: independent reviewer. Notion: source originals. Cortex: derived knowledge and outputs.
