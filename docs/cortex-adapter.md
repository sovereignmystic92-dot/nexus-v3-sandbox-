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

These adapter tests use offline transports. Earlier C01–C03 Cortex tool exercises are separate live observations. The subsequent C05 probe below directly exercised this Python adapter against live Cortex. Hosted validation is recorded separately after execution. The existing hosted runner also exercises four bounded coordinator faults; those are not Cortex network-failure tests.

The exposed Cortex update tool has no expected-version/CAS parameter. Preflight and post-write reads cannot prevent another writer from racing between calls. Only one worker may own the journal and fixture names. Concurrent writers, atomic cross-module consistency, production use and automatic retries after uncertain writes remain outside acceptance. Full foundation acceptance remains blocked by the wider audit gates.

## Observed hosted run

[Run 39881697563](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39881697563), source commit `9aeb79bc3d972c5dc2f11a8e08dda8e1743904d9`, passed 52 offline tests, all four mission scenarios and four bounded coordinator fault checks. Host and container boundary probes passed; container removal and source-staging cleanup were reported successful. The adapter-specific cases remained offline. Exact source hashes, case results and limitations are retained in [the hosted report](hosted-run-39881697563.json). Full foundation acceptance remains `BLOCKED`.

## C05 live adapter validation

The unchanged adapter and bridge from tested commit `9aeb79bc3d972c5dc2f11a8e08dda8e1743904d9` were invoked by [the explicit C05 probe](cortex-c05-probe.py) through a host-authenticated JSON-line callback. The local Python process received original Cortex tool-result dictionaries; it received no credentials or direct network client. This probe is an operator-mediated integration test, not an installed autonomous service. It creates only three explicitly named C05 synthetic fixtures and never modifies the C01 source.

The first Python process made 25 reads and three creates. A stale source version was blocked. Archive and registry creation independently verified; an output acknowledgment deliberately discarded locally after its successful real tool reply produced an uncertain result, then reconciled without a second create. This did not simulate a real network interruption. Every stage was repeated and verified without a further write.

A second Python process reopened the same SQLite journal and made 27 reads with zero writes. All three IDs and version 1 matched the first process. An independent registry Flash matched four module contents and three dependency edges. SQLite integrity was `ok`, with four receipts and seventeen events. The [public result](cortex-c05-live-result.json) uses aliases for actual account module IDs; exact bindings and IDs are retained in the scoped Cortex C05 evidence issue.

Live creation, reconciliation and process restart are now observed for this adapter. Live updates, stale target conflict preservation, concurrent writers, long-term durability and full production acceptance remain unverified. The next bounded validation is a live update with its exact target baseline and independent metadata readback. Notion integration remains paused.
