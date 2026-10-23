# Synthetic Cortex adapter

This draft adds a reusable, single-worker persistence adapter to the mission-scenarios branch (PR #2). It is independent of the paused Notion adapter in PR #3. It does not activate production Nexus or automatically invoke Cortex.

## Host contract

`CortexAdapter(journal_path, exact_name_allowlist, transport).ensure(Write(...))` accepts an immutable synthetic request. The source is an exact `Module` snapshot; an update also requires an exact target snapshot in `before`. Content must begin with `TEST FIXTURE — SYNTHETIC — NOT CANONICAL.` and contain its `synthetic:request:` key. Every source, target and declared dependency must be in an explicit allowlist of names beginning with `Nexus Sandbox `.

The host supplies `CortexToolTransport(invoke)` with an authenticated callback for the existing Cortex `context_get`, `context_create` and `context_update` tools. The callback returns the tool-result dictionary and propagates call failures. This repository contains no credentials, live callback registration, scheduler or direct network client. The caller must bind the callback to the intended Cortex account and retain the SQLite journal across restarts.

The bridge only maps the exact observed missing-module result (error code `INVALID_ARGUMENT` plus the sole text `module matching query does not exist`) to absence. Other errors, malformed results and timeouts remain unknown. A changed service response contract must be reviewed rather than treated as absence. Updates send only name, content and dependencies; ownership, parent, permissions and assignees are omitted.

## Checkpoints and evidence

Before any side effect, one SQLite transaction stores the immutable request binding, write intent and event. A reused key with different content, source, dependencies or baseline is rejected. After an uncertain write or restart, the adapter reads the bound name and never automatically repeats the write. If the desired state is absent or different, it holds for investigation.

Completion requires fresh source and target reads matching identity, version, content and dependencies. A new target must be version 1; an update must preserve target ID and increment the pinned version once. Successful transport calls and protocol verification are separate fields: a successful write can have an unknown, failed or blocked protocol result. Reconciliation can verify a prior write while reporting `NOT_ATTEMPTED` for the current invocation. An unacknowledged create can only be reconciled by exact bound name, content, dependencies and version until its ID has been independently observed.

The adapter preserves mismatched remote state and withholds completion if the source changes. It neither repairs nor deletes modules automatically. Dependencies are validated as allowed names, not recursively fetched or certified by this adapter. Per-write receipts can be composed into archive/output/registry stages; they do not by themselves implement a mission scheduler or a cross-service transaction.

## Validation and limits

Local suite: 52 distinct tests (32 existing plus 20 adapter/bridge tests). Cases include missing and changed sources, stale target versions, malformed/missing tool responses, immutable bindings, uncertain acknowledgments, a simulated process stop, failed journal commits, source changes during a write, readback outages and three-stage reuse across journal reopenings.

These adapter tests use offline transports. Earlier C01–C03 Cortex tool exercises are separate live observations and are not proof that this new Python adapter has run against Cortex. Hosted validation is recorded separately after execution. The existing hosted runner also exercises four bounded coordinator faults; those are not Cortex network-failure tests.

The exposed Cortex update tool has no expected-version/CAS parameter. Preflight and post-write reads cannot prevent another writer from racing between calls. Only one worker may own the journal and fixture names. Concurrent writers, atomic cross-module consistency, production use and automatic retries after uncertain writes remain outside acceptance. Full foundation acceptance remains blocked by the wider audit gates.
