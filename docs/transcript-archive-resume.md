# Archive resume planner

`plan_archive_resume` in `transcript_ingestion_gate.py` is an offline, provider-neutral decision function. It does not execute writes, persist a recovery journal, authenticate responses, or schedule a host. The existing SQLite coordinator is unchanged; a real YouTube ID is not invented for supplied-message sources.

The trusted single-worker host must pin the source digest and exact provider destination independently of observations. Supply prepared exact chunks and a fresh, fully paginated observation containing `destination`, `source_sha256`, `complete: true`, and ordered `{index, text}` records. The completeness flag is a host assertion, not independent proof supplied by this library.

- Unknown outcome / no observation: `READBACK_REQUIRED`, empty write plan.
- Complete observation with missing chunks: `MISSING_CHUNKS`, only absent indexed payloads returned.
- Complete exact archive: `ARCHIVE_VERIFIED`, empty plan.
- Wrong binding, incomplete pagination, malformed source, conflicting text, duplicate or unordered indices: ValueError, no plan.

The host must preserve logical index order when inserting missing chunks; sparse gaps cannot be repaired by blindly appending. After each uncertain write, discard any old plan and independently read again before replanning. Before executing any plan the host must retain its separately established authorization and exclusive ownership; this planner supplies no lease, CAS or stale-snapshot protection. It cannot protect a concurrent writer between observation and execution. Never use a plan itself as write authority.

Every returned decision keeps provider/Cortex write authority and audit promotion false. Require a new complete exact readback after planned writes before advancing the stage journal. A checksum authenticates neither the provider nor the claim content.

Validation: `PYTHONPATH=src python -m unittest discover -s tests -p test_transcript_fidelity.py -v` — 32 local offline tests passed, including nine planner methods. One Linux-only method runs two actual owned-child SIGKILL scenarios: before the missing write, and after a file-backed fake-provider write is flushed/fsynced but before acknowledgment. A separate process reloads persisted source and fake-provider observation; it plans the missing chunk in the first case and no writes in the second. Actual child-process crashes are covered against a file-backed fake provider. Real provider timeouts, mid-write crashes/torn fake-provider files, power loss, OAuth, live writes, concurrent-worker and unattended recovery are not covered. Existing dedicated CI covers these same files; workflows, inventory fingerprints and credentials are unchanged.


## Durable provider host (bounded integration)

`ArchiveRecoveryHost(journal_path).attempt(...)` wires the planner to injected
`read_archive(destination, source_sha256)`,
`write_chunk(destination, source_sha256, index, text)`, and
`authorize_write(destination, source_sha256, index)` callbacks. Authorization
must return literal True after checking current effective grants; it is separate
from the planner's non-authorizing output. This package supplies no Notion HTTP
client, credential, platform connector, runner registration or scheduled trigger.

The host pins a complete prepared source and destination in SQLite, rejects
rebinding before any provider call, commits intent before side effects, and holds
a nonblocking advisory lock over the whole attempt. The directory and journal
must be trusted, persistent, on a supported local Linux filesystem, and exclusive
to this archive. Do not delete or replace journal/lock files during operation.
Every cooperating local worker must use the same path. This is not distributed
fencing, authenticated journal history, power-loss proof or defense against
uncooperative writers.

Each attempt performs a new read, writes at most one missing chunk, then reads
again. A write acknowledgment never establishes success. A reader must return
authenticated, complete, strongly consistent, ordered observations or raise/return
None; a partial listing must not claim completeness. The writer must preserve
logical index order. Callbacks must enforce network/request deadlines; the class
does not interrupt hanging provider calls.

An unresolved prior intent whose chunk is absent blocks automatic retry.
An optional `confirm_absent(destination, source_sha256, index)` callback must
return literal True only when the host has established a settled non-commit and
that the earlier request cannot still complete. A listing miss or timeout alone
is insufficient. Without such proof, stop for reconciliation. A prior intent
whose exact chunk is observed does not replay that chunk.

This is a separate archive journal; it does not mutate the legacy YouTube-only
TranscriptCoordinator or complete downstream analysis/Cortex stages. Callers
may record an archive stage only after ARCHIVE_VERIFIED and actual provider
identity/readback requirements are satisfied.

Validation: 41 local offline tests passed. Nine new host methods cover bounded
writes, fresh readback, uncertain absence hold/release, denied authorization,
destination binding, incomplete listings, local lock exclusion, durable intent,
and an actual owned-child SIGKILL after a flushed/fsynced file-backed fake-provider
commit. A new process reopens the same SQLite journal and verifies with zero
duplicate writes. No live Notion provider callback was executed in these tests.
