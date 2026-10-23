# Synthetic Cortex adapter

This draft adds a reusable, single-worker persistence adapter to the mission-scenarios branch (PR #2). It is independent of the paused Notion adapter in PR #3. It does not activate production Nexus or automatically invoke Cortex.

## Host contract

`CortexAdapter(journal_path, exact_name_allowlist, transport).ensure(Write(...))` accepts an immutable synthetic request. The source is an exact `Module` snapshot; an update also requires an exact target snapshot in `before`. Content must begin with `TEST FIXTURE — SYNTHETIC — NOT CANONICAL.` and contain its `synthetic:request:` key. Every source, target and declared dependency must be in an explicit allowlist of names beginning with `Nexus Sandbox `.

The host supplies `CortexToolTransport(invoke)` with an authenticated callback for the existing Cortex `context_get`, `context_create` and `context_update` tools. The callback returns the tool-result dictionary and propagates call failures. This repository contains no credentials, live callback registration, scheduler or direct network client. The caller must bind the callback to the intended Cortex account and retain the SQLite journal across restarts.

The bridge only maps the exact observed missing-module result (error code `INVALID_ARGUMENT` plus the sole text `module matching query does not exist`) to absence. Other errors, malformed results and timeouts remain unknown. A changed service response contract must be reviewed rather than treated as absence. Updates send only name, content and dependencies; ownership, parent, permissions and assignees are omitted.

## Checkpoints and evidence

Before any side effect, one SQLite transaction stores the immutable request binding, write intent and event. A reused key with different content, source, dependencies or baseline is rejected. After an uncertain write or restart, the adapter reads the bound name and never automatically repeats the write. If the desired state is absent or different, it holds for investigation.

Completion requires fresh source and target reads matching identity, version, content and dependencies. A new target must be version 1; an update must preserve target ID and increment the pinned version once. Successful transport calls and protocol verification are separate fields: a successful write can have an unknown, failed or blocked protocol result. Reconciliation can verify a prior write while reporting `NOT_ATTEMPTED` for the current invocation. Before the first VERIFIED event has been durably recorded for a create request, reconciliation uses the exact bound name, content, dependencies and version. Merely observing a target ID in a blocked source-change or readback-failure path does not pin it. After a VERIFIED event is durably recorded, the earliest such event anchors the create identity; update identity is bound in the exact before snapshot.

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

Live creation, reconciliation and process restart are now observed for this adapter. At the C05 checkpoint, live updates and stale target conflict preservation were still unverified; C06 below subsequently tests both. Concurrent writers, long-term durability and full production acceptance remain unverified. Notion integration remains paused.

## C06 live update and stale-target validation

[The explicit C06 probe](cortex-c06-probe.py) exercised the same adapter and bridge against the C05 synthetic registry with an exact version-1 baseline. One update advanced the module to version 2 while preserving its ID. Independent reads verified exact content, dependencies, owner, parent, permission inheritance, default assignee, creation timestamp and archived status. Repeating the same request performed no write. A separate request retaining the old version-1 baseline was blocked at `TARGET_CONFLICT`; a subsequent read confirmed the version-2 state was preserved.

The probe made 13 reads and exactly one update. An independent Flash matched all four module contents and three dependency edges against the saved C05 bindings, with only the intended registry content changed. The journal passed its integrity check with two receipts and four events. See [the public result](cortex-c06-live-result.json); exact bindings are retained in the scoped Cortex C06 evidence issue. No live adapter implementation changed.

The registry is now version 2. C05 records describe its earlier version-1 observations; rerunning the old C05 probe against the updated fixture is expected to hold rather than overwrite it. The C06 probe also refuses a fresh update unless the target is version 1; retain its journal and reconcile uncertain state rather than resetting it.

This proves one bounded live update and preservation after a stale sequential request. It does not provide atomic compare-and-swap, protection from concurrent writers, uncertain-update recovery, power-loss or long-term durability proof. Review remaining audit acceptance gates and the stacked PR merge order before promotion. Full foundation acceptance remains `BLOCKED`; Notion integration remains paused.

## C10 merged main and C11 uncertain-update recovery

PR #4 was subsequently owner-approved and merged at `62265e0d5bf3f371b965eab7f953dc9230501eaf`. [Actual main run 39889605147](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39889605147) passed 52 tests and four separately counted bounded coordinator faults. Earlier draft/merge-pending statements describe historical checkpoints.

C11 then exercised that unchanged adapter and bridge through [an explicit two-process live probe](cortex-c11-probe.py). The first process made four reads and exactly one update of the synthetic registry from v2 to v3. After the actual successful service reply arrived, the host callback discarded it locally and raised a timeout. The adapter reported `UNKNOWN/UNKNOWN/RECONCILE_ONLY` and preserved durable intent.

A second actual Python process reopened the original immutable plan and SQLite journal. Writes were disabled in both the probe transport and host guard for this phase. Eleven gets verified the original ID, exact v3 content/version/dependencies, write-free repeat and a blocked stale v2 request. Independent metadata readback preserved owner, parent, permission inheritance, default assignee, creation timestamp, archived state and dependencies. Flash matched four module contents and three edges, with source/archive/output unchanged. SQLite integrity was ok, with two receipts and five events.

See [public result](cortex-c11-live-result.json). Exact IDs, original request and checkpoint evidence are retained in the scoped Cortex C11 issue. One uncertain live-update acknowledgment is now observed to recover without duplicate write across a normal process exit/restart. This is a deliberate local reply discard, not a real network outage, abrupt process kill, power loss, CAS/concurrency guarantee or long-term durability proof. The registry is now v3; prior C05/C06 probe baselines are historical and must not be replayed blindly. Full acceptance remains BLOCKED; Notion remains paused.

## Independent AI review and trusted-history operating rule

A separate AI reviewer inspected frozen merged revision `618681fdc6d1767358cca993e857f68fd2202879` in a fresh directory and independently reproduced the 56-test suite, four critical regressions and seven additional adversarial cases. The four regressions failed the baseline adapter as expected. [The attributed report and raw evidence](independent-review/independent-review-report.md) recommend the narrow first-persisted-VERIFIED / before-ID correction with intact trusted history and one worker; no blocking defect was found within that boundary. This does not establish independent human audit or independently rerun hosted/live fault tests.

Retain complete, unmodified event history. Deleting or truncating create history can lose the original identity anchor even when the latest receipt still contains the old ID. There is no automatic missing-history detection, authentication or tamper protection. Do not reset or compact journals without preserving the original verified identity. IDs observed before a durable VERIFIED event—including a successful write followed by source-change hold—are not pinned by this implementation. These independently demonstrated limitations must remain in any acceptance claim. This documentation clarification changes no runtime code. Full foundation acceptance remains BLOCKED; Notion stays paused.
