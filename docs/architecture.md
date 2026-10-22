# Proposed architecture

Scope: one worker, synthetic records, SQLite, no integrations. No runtime exists in this draft.

| Component | Contract | Draft status |
| --- | --- | --- |
| Authority resolver | Separate current, historical, source and hypothesis material; hold on unresolved governing conflicts | Specified only |
| Transaction manager | Bind stable idempotency key to source revision, destination and payload hash; reject changed payload under reused key | Specified only |
| Evidence validator | Require complete source and attributable claims before progression | Specified only |
| Routing controller | Permit only explicit synthetic destination IDs | Specified only |
| Persistence verifier | Reopen storage separately; compare exact persisted IDs, destination and content hash before VERIFIED | Specified only |

## Proposed transaction progression

NEW → VALIDATED → ARCHIVED → OUTPUT_CREATED → REGISTERED → VERIFIED.

BLOCKED and INCOMPLETE are non-success dispositions with a preserved last-confirmed checkpoint and explicit resume action. They never erase the prior confirmed state. Acknowledged writes do not imply VERIFIED. A transaction becomes VERIFIED only after independent readback evidence matches expected content and location.

Use a SQLite transaction to update checkpoint, version and corresponding event atomically. Retrying the same idempotency key returns existing state; changing its immutable binding is an error. Recovery must inspect actual artifacts before creating replacements. This design does not claim cross-service atomicity.

Concurrent workers and stale-worker fencing are out of initial execution scope. The version column is a proposed prerequisite, not proof that fencing is implemented. Event rows are append-only by controller contract; the draft schema alone does not prevent a privileged SQLite writer from altering history.
