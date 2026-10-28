# Existing Notion adapter compatibility assessment

Inspected current main f79bef4591850259af675b27c58d0d097969f4ce and the existing notion-adapter branch for PR #3. Assessment only; PR #3 remains unchanged.

## Reuse decisions

- Keep main's synthetic coordinator and Cortex fixture boundaries intact. They are tested components, not a general production controller.
- Reuse the Notion adapter's immutable request binding, intent-before-create pattern, known-ID readback, duplicate ambiguity hold and reconcile-only behavior after uncertain create.
- Adapt the record representation: PR #3 expects a synthetic-marked JSON fixture; the real transcript is an ordinary Notion page with manifest and raw section. Never relabel real content synthetic to make checks pass.
- Keep source and derived-output bindings separate: their payloads legitimately differ. The synthetic coordinator's same-payload artifact invariant cannot be copied literally.
- Replace title-search assumptions with an explicitly complete, paginated, scoped lookup contract. Existing connected search results do not prove duplicate absence.
- Establish durable private journal custody and recovery identity before using create intents for real records. Scratch SQLite is not a surviving execution service.
- Retain single-worker scope. Sequential reads are not provider-side compare-and-swap, atomic commit, remote fencing or protection against other clients writing.
- Validate typed observations strictly. A truthy completeness field is not explicit boolean completeness. New read-only gate requires actual True and exact types.
- Preserve existing source and output IDs for the pilot; do not recreate them to demonstrate idempotency.

## Rollout sequence and completion criteria

1. Review/adopt the additive read-only bridge separately. It evaluates real host-fetched observations but is not yet a mandatory execution gateway.
2. Define the host transport's typed observation and complete-lookup behavior and exact parent allowlist, and a trusted durable journal with explicit restore behavior. Implement against fake transports first using existing adapter mechanisms.
3. Prepare one bounded draft-write operation and its exact permitted destination for review. No credential scope expansion or production activation follows from this assessment.
4. Exercise one authorized operation through the controller, then a same-request repeat and reconciliation after a simulated lost acknowledgment. Distinguish local simulation from real-provider observations.
5. Require independent source/output readback, no duplicate write on repeat, correct hold on incomplete lookup and uncertain outcome, and restart from the last confirmed state.

Current status: read-only observation code tested locally; current-main integration checks pending. Duplicate prevention, controlled real writes, durable recovery, automatic invocation and full Nexus integration remain NOT PROVEN. No gate count changes.
