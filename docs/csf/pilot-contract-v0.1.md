# CSF pilot contract v0.1 (proposal only)

Issue: #189. Status: **draft / not deployed**.

## Scope
Enrich an **existing** Haiti/WarFronts transcript in read-only mode, limited to two pilot tags: `governance` and `infrastructure`. The full taxonomy may later include technology, energy, geopolitics, industry, demographics and climate. Infrastructure is a cross-cutting pilot tag, not a replacement for the seven-domain taxonomy.

## Record contract
Each enrichment record MUST carry:
- `contract_version`: `"0.1.0"`
- `source`: original transcript identifier, canonical Notion reference, source revision and content digest
- `target`: existing Cortex module identifier and revision (null means **no persistence allowed**)
- `claim_id`: stable identifier scoped to source and revision
- `claim_type`: `observation | inference | scenario`
- `domains`: subset of `governance | infrastructure` for pilot
- `statement`: attributed claim, not asserted truth by default
- `evidence`: exact source offsets or independently resolvable citations
- `relations`: typed, directed links to other claim IDs with explicit causal uncertainty
- `uncertainty`: qualitative uncertainty and reason; no invented numeric confidence
- `counterevidence`: citations or explicit `not_checked`
- `review`: reviewer identity, status, evidence artifact reference
- `idempotency_key`: deterministic digest of source ID, source revision, contract version, and claim ID

## Safety invariants
1. Original full-fidelity transcript is immutable; derived findings are separate.
2. Never create a second Cortex module when identity resolution is uncertain.
3. No live Notion/Cortex writes, external dispatch, merge, or deployment in this pilot PR.
4. An agent may propose a claim but may not independently certify it.
5. Unsupported claims remain hypotheses; contradictions are preserved.
6. Unknown schema versions and invalid transitions fail closed.
7. GitHub event delivery alone does not prove Gemini, Codex or Cortex executed.

## Durable handoff state machine
`INVENTORY_PENDING → SOURCE_VERIFIED → CONTRACT_READY → IMPLEMENTED → TESTED → INDEPENDENT_REVIEWED → OWNER_APPROVED → PERSISTED`

Each transition requires an actor, UTC timestamp, linked evidence, and an outcome; failures are explicit. `PERSISTED` additionally requires independently verified target identity and explicit authorized write path.

## Acceptance test plan
- Source text and digest unchanged before/after enrichment.
- Repeat ingestion yields the same idempotency keys and no duplicate findings.
- Missing Cortex identity blocks persistence.
- Claims without evidence cannot pass validation as observations.
- Review actor differs from proposing actor; missing Gemini review remains pending.
- Existing policy/adapter checks still pass.
- Audit output records actor, evidence and failure reason for each transition.

## Work assignments
- Chat: specification and coordination.
- Codex: inspect current adapters and implement a minimal schema validator and synthetic dry-run tests.
- Gemini: independent review of test artifact and counterhypotheses; do not claim review without execution evidence.
- GitHub Actions: run tests and retain results.
- Notion: original source archive; Cortex: persistent derived output only after approval.
- Owner: scope, permissions and deployment decisions.
