# CP06 recovery adjudication

Assessor: ChatGPT author assessment under recorded owner standing approval. Definition proposal-1 and requirement wording unchanged. Proposed verdict: PASSED; tracker 11/19 only after merge and readback.

## Declared fault boundary

The requirement's evidence definition already calls for a declared local-state fault domain and explicit excluded physical faults. This assessment covers the complete disposable local persistent-data directory: combined coordinator/adapter SQLite database, transaction/artifact/connection/endpoint records, adapter receipts/events/identity anchors, recovery inventory and original backup files. The entire directory was deleted, not merely a database file.

The host and authenticated provider connection survive. Notion and Cortex retain the private checkpoint copies/manifests. A freshly fetched current GitHub main contains only sanitized sequence/hash commitments. Physical VM/device/power loss, compromised administration, provider outage, long-term retention and production recovery are excluded observations, not assertions of safety.

## Requirement evidence

Declared crashes/storage faults: positive main [run 40142926229](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/40142926229) at 409110a769fd668fa6538ce0d0b8ebc7a416198b passed 198 distinct cases plus four actual bounded coordinator faults (three owned-child SIGKILL cases and tmpfs ENOSPC/SQLITE_FULL). Existing corruption, interrupted restore, missing-inventory holds and backup checks remain covered.

Protected current authority: the active default-branch ruleset was freshly read as requiring PR/strict synthetic checks and denying deletion/non-fast-forward updates, with no bypass actors. Required approving-review count remains zero; recorded owner standing authorization is operational policy, not an enforced independent human review. The host checker fetches the exact GitHub base/first parent and rejects truncation or rewriting. Public references contain no provider IDs, installation identity or recovery payload.

The initialized second public commitment was freshly fetched after adoption. Fresh Notion/Cortex packet and private-manifest reads matched that commitment, exact provider identities, installation, packet hashes and event sequence. No cached local latest record selected the packet.

Cold local-state restoration: after deleting the whole declared directory, the exact database bytes were restored. A separate Python process verified the original coordinator checkpoint, exact committed artifacts and typed reciprocity, and unchanged coordinator records. The recovered Cortex adapter reconciled the real synthetic Cortex target twice against original dictionaries from fresh live tool reads, with NOT_ATTEMPTED/VERIFIED outcomes and zero transport writes. This is an explicitly host-mediated read-only observation bridge, not an autonomous network client or a new live write attempt.

Stale/corrupt copies: the older mutually matching pair plus its older manifest was rejected under the current public commitment. Old copies under the current manifest and coherently corrupted current copies also held before creating local recovery state.

Actual hosted rollback denial: [negative run 40142945425](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/40142945425) tested a candidate differing only by deliberate ledger truncation. The required check returned checkpoint_ledger REJECTED with exact reason Public accepted history truncated, before container execution. PR #33 was closed and never merged. Earlier PR #30 gave a generic subprocess error and is retained as limited historical evidence, not substituted for this precise result.

## Decision and constraints

All conjunctive CP06 conditions are satisfied for the explicitly declared current synthetic fault boundary. No pass requirement, checkpoint identity or denominator was changed. This does not pass the still-open host/grants/credential/trigger/cleanup/fencing/human-review gates or activate production. Trust in the GitHub service, authenticated current-ref retrieval and reviewed validation code is explicit; deliberately removing that validator or administrator compromise is not covered.

Detailed routing, installation metadata, private manifests and recovery payloads remain only in authorized Notion/Cortex sandbox records. Public evidence is sanitized. Historical observations and blockers remain in register history. Relevant implementation/configuration change requires impact assessment; failure or loss of the current evidence reopens the gate.
