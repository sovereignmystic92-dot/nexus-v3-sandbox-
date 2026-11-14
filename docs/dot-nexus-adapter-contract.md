# Dot-to-Nexus Adapter Contract (proposal, not active integration)

Status: DESIGN ONLY. Dot availability, account limits, external actions, and delivery mechanisms are unverified. This document does not authorize live execution.

## Objective
Accept proactive agent findings as **untrusted proposals** through the existing Module Evolution event intake, without granting agents governance authority, trading permission, or readiness advancement.

## Five module destinations
- `skill_forge`
- `personal_growth_forge`
- `field_journal`
- `civilization_engine`
- `trading_platform`

One Dot may cover all five modules; multiple Dots may specialize. No one-Dot-per-module requirement.

## Proposed envelope (version 1)
```json
{
  "schema_version": "dot_nexus_event_v1",
  "event_id": "opaque-unique-id",
  "origin": {"kind": "dot", "agent_id": "opaque-id"},
  "observed_at": "2026-11-10T23:00:00Z",
  "module_hints": ["skill_forge"],
  "subject": "human-readable claim",
  "source_refs": [{"uri": "https://example.org/source", "sha256": null}],
  "proposed_action": "review",
  "evidence_status": "UNVERIFIED",
  "idempotency_key": "opaque-stable-key"
}
```
The example is illustrative, not a claim that a Dot can emit this format today.

## Acceptance gates
1. Authenticate the delivery channel and identify the sender. Never treat an agent-provided `agent_id` as proof of identity.
2. Validate schema, bounded sizes, supported modules, permitted action types, and source references; reject malformed and conflicting duplicate identities.
3. Store immutable raw intake and a durable idempotent receipt; verify cross-run readback before enabling live ingestion.
4. Quarantine external text as untrusted data. No instruction execution from retrieved pages, transcripts, or agent summaries.
5. Resolve source fidelity and attribution. Notion holds original transcripts/journals; derived outputs belong in Cortex only when authorization is confirmed.
6. Require independent review and existing Nexus governance gates before readiness changes, publication, merges, or other privileged effects.
7. Default status is `PENDING_VALIDATION` and `readiness_advanced=false`; a proposal alone cannot upgrade readiness.
8. Trading proposals are research-only. No orders, credentials, transfers, or autonomous brokerage execution through this adapter.
9. Log decision, reviewer, evidence links, and rejection reason without exposing secrets.

## Delivery options, contingent on supported Dot capabilities
A. Human-mediated submission of a structured finding to Nexus (safe initial pilot).
B. Approved connector or webhook relay with authenticated delivery and replay protection, only if the product supports it.
C. Scheduled GitHub ingestion from an explicitly authorized source; do not claim direct Dot-to-GitHub triggers without verification.

## Acceptance tests to add
- Valid proposal routes to each of five modules and remains pending.
- One agent may address multiple modules without duplicating receipts.
- Exact replay is idempotent across separate workflow runs.
- Conflicting duplicate, unknown module, missing evidence, spoofed origin, and untrusted embedded instructions fail closed.
- No credentials, Cortex writes, live trades, or readiness advancement in offline acceptance.

## Rollout
Phase 0: this design. Phase 1: synthetic offline adapter tests. Phase 2: durable cross-run storage and readback. Phase 3: authenticated live intake only after Dot capabilities and authorization are verified. Phase 4: independent review of any readiness-advancing actions.
