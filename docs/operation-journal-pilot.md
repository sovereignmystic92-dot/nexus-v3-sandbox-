# Reusable operation journal — implementation draft

This builds on PR #3's immutable-binding and intent-before-create mechanisms,
separating them from synthetic fixture layout. Neither the old fixture checks nor
the existing coordinator is relaxed.

Operation identity binds key, source ID, source revision, destination UUID and
intended payload SHA-256. Raw payloads are not stored. The caller still owns
source verification, title/metadata coverage, authorization and trusted transport.

An explicitly initialized private SQLite journal commits WRITE_INTENT before
returning MAY_ATTEMPT_WRITE. That return is bookkeeping, never provider authority.
Every repeat returns RECONCILE_ONLY, even if the process stopped before sending
anything. Known remote IDs are pinned; changed IDs or changed operation bindings
hold. Acknowledgment does not verify content. Reconciliation invokes the read-only
verifier; only a matching fresh callback observation can yield
VERIFIED_OBSERVATION. It does not prove duplicate absence or complete lookup.

Missing journals cannot silently recreate themselves on reopen. Initialization
refuses an existing file, creates with mode 0600, and requires an explicit identity.
SQLite FULL synchronous commits are local durability controls, not evidence of
surviving host loss. Identity is caller-supplied, not an external trust anchor.
Restoring or replacing an entire journal and multi-worker/provider fencing remain
outside this contract. One trusted worker and one trusted journal are required.

Validation: ten journal tests plus eight readback tests passed locally. Tests cover
reopen after intent, uncertain-create candidate reconciliation without any create
callback, changed bindings, acknowledgment/readback separation, changed remote
identity, mismatched/read-failed observations, missing journal, wrong identity,
existing-file initialization and absence of raw payload storage. Two sequential
handles demonstrate shared intent visibility, not independent-worker fencing.

No real mutation, service timeout or actual killed-process recovery was executed
for this new journal. Restart tests reopen local state, not provider-backed host
loss. There is no Notion create transport or automatic execution path here.

## Remaining integration work

Configure and independently verify durable private journal custody; implement
complete scoped candidate lookup and typed ordinary-Notion-page transport; bind
source and output separately; then prepare one exact authorized draft-write pilot.
Existing transcript/output records must be reused, not recreated. Real recovery,
duplicate prevention and mandatory invocation remain unproven until actual
operations pass through that path. No production activation or gate promotion.
