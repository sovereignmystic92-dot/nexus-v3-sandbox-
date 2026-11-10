# Nexus Module Evolution — event-driven contract (draft)

Related: #298. Status: design-only; not an installed runner.

## Permanent modules
- skill_forge
- personal_growth_forge
- field_journal
- civilization_engine
- trading_platform

## Event intake
Evaluate supported GitHub events: push, pull_request, issues, workflow_run. Record repository, delivery/event identifier, event type, subject SHA/ID, source URL, timestamp, and provenance. Normalize events into a versioned envelope. Use least-privilege read permissions for untrusted events; never execute PR-supplied code with privileged tokens. Evaluate events, but do not assume every event constitutes progress.

## Routing and evidence
Classify zero or more modules per event. For each candidate record the contribution, source reference, evidence class (offline, synthetic, authenticated read-only, live write), validation outcome, and relevant Foundation Audit checkpoint. Only validated evidence may advance readiness. Unverified contributions remain pending, not discarded. No automatic expansion of grants or authorization.

## Durability and safety
Use idempotency keys based on immutable event identity and module; duplicate delivery must not double-count. Durable receipts must survive restart and support independent readback. Prevent self-trigger loops from status commits or bot-generated events; bound retries and concurrency. Fail closed for missing grants, malformed payloads, and unknown external results. Keep source records in their designated authoritative store; Cortex derived output is gated by verified access. No provider writes in this draft.

## Acceptance test plan
1. A real ordinary workflow event is ingested and linked to at least one module.
2. A duplicate event does not create a second advancement.
3. A non-contributing event leaves readiness unchanged.
4. An untrusted PR cannot access write credentials or privileged execution.
5. A process restart retains evidence and produces an independent readback.
6. Five consecutive qualifying workflow-to-module updates are verified, with provenance, no lost records and no unauthorized changes.
7. A scheduled reconciliation identifies missed events without manufacturing progress.

## Initial implementation boundary
Build a runner and offline tests on a draft PR after reconciling existing workflows, constitution, and policy contracts. No deployment, merge, autonomous Codex installation, Notion/Cortex provider write, or live trading is implied by this document.
