# Durable solution handoff outbox

This opt-in outbox turns a recorded finding into accountable work without treating
delivery as resolution. It reuses Nexus's durable-journal pattern: immutable
bindings, explicit state, append-only receipts, restart readback, and no blind
retry after an uncertain external effect.

Public lifecycle:

`RECORDED → ROUTED → ACCEPTED → IN_PROGRESS → VERIFIED_COMPLETE`

`ROUTING` is an internal reconciliation state committed before delivery. If the
delivery callback times out or returns an invalid receipt, the handoff remains in
`ROUTING`; a host must inspect the destination before confirming delivery or
blocking it. `BLOCKED` requires both the exact blocker and a reopening trigger.
Reopening returns the item to `RECORDED` while retaining its event history.

Each immutable handoff binds a stable finding ID, source reference/revision,
destination, smallest next action, completion criteria, authorization reference,
and priority. A reused finding ID with different bindings is rejected. Completion
requires both a result evidence reference and a distinct independent-readback
reference. Delivery and acceptance are never counted as completion.

`deliver_one` is the bounded host integration point. It selects one recorded item,
commits `ROUTING`, then invokes an injected callback. A successful callback must
return exactly one bounded `delivery_ref`; otherwise the saved state remains
uncertain and the outbox will not call it again. The host still authenticates the
destination, actor, evidence, authority, and readback.

This change installs no listener, schedule, GitHub issue writer, Cortex transport,
credential, provider authority, multiworker fencing, or production activation.
SQLite is single-worker local custody and does not survive host loss unless the
caller supplies durable storage. Adopting the library therefore does not itself
make handoffs unattended. A separately reviewed consumer must call it from an
authorized controller and reconcile `ROUTING`, `ROUTED`, and `BLOCKED` items.

For transcript work, Notion references identify the canonical original transcript
and provenance. Cortex references identify derived analytical outputs. The outbox
does not carry transcript content and must not be used to bypass the mandatory
supervised transcript analysis gate.

Validation:

```sh
PYTHONPATH=src python -m unittest tests.unit.test_handoff_outbox -v
```

Synthetic tests cover the full receipt chain, delivery, lost acknowledgment,
deduplication, conflict rejection, invalid state skipping, blocking/reopening,
restart readback, and custody identity mismatch. They make no live-provider,
durability, authentication, or independent-review claim.
