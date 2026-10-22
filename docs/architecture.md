# Proposed architecture

Scope: one worker, explicit synthetic fixture catalog, SQLite, no integrations. A local coordinator now exists; no hosted runtime is provisioned.

| Component | Contract | Draft status |
| --- | --- | --- |
| Authority resolver | Separate current, historical, source and hypothesis material; hold on unresolved governing conflicts | Structured synthetic metadata resolver implemented locally; no natural-language or authenticated authority assessment |
| Transaction manager | Bind stable idempotency key to source revision, destination and payload hash; reject changed payload under reused key | Implemented locally; complete flag also bound |
| Evidence validator | Require complete source and attributable claims before progression | Fixture completeness/hash enforced; claim attribution not implemented |
| Routing controller | Permit only explicit synthetic destination IDs | Implemented locally; no external adapter |
| Persistence verifier | Reopen storage separately; compare exact persisted IDs, destination and content hash before VERIFIED | Implemented locally; snapshot observation only |

## Proposed transaction progression

NEW → VALIDATED → ARCHIVED → OUTPUT_CREATED → REGISTERED → VERIFIED.

BLOCKED and INCOMPLETE are non-success dispositions with a preserved last-confirmed checkpoint and explicit resume action. They never erase the prior confirmed state. Acknowledged writes do not imply VERIFIED. A transaction becomes VERIFIED only after independent readback evidence matches expected content and location.

Use a SQLite transaction to update checkpoint, version and corresponding event atomically. Retrying the same idempotency key returns existing state; changing its immutable binding is an error. Recovery must inspect actual artifacts before creating replacements. This design does not claim cross-service atomicity.

Concurrent workers and stale-worker fencing are out of initial execution scope. Version checks reject stale checkpoints, but no worker lease/fencing mechanism exists. Event rows are append-only by controller contract; the schema does not prevent a privileged SQLite writer from altering history. Source payloads are copied literally and never evaluated as code or interpreted as authority. Synthetic markers are caller assertions, not an automatic detector of real data.

Every committed transition now includes an attributable attempt envelope referenced by its event. The governing authority revision is bound to the transaction; authority drift holds the last checkpoint. See authority-and-acceptance.md for exact scope and the blocked full-acceptance verdict.
