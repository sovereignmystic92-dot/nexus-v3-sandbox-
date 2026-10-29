# Bounded checkpoint resume validation

This work extends existing draft PR79; it does not create a new executor, trigger or persistence framework. The read-only entrypoint wraps adopted resume_decision. Host --inventory-complete and --authority-verified remain caller assertions, not authenticated evidence or live execution permission. Binding input now rejects duplicate keys and nonfinite JSON with the adopted strict decoder.

## Recorded enrollment
The fixture saved-enrollment-40862662915.json is the exact sequence0 event observed on the canonical Foundation Audit after write run40862662915 attempt1 and read-only attempt2. Its checkpoint SHA-256 is 7409a0f2aae701d8d1c4cbce51426d96f455ec989f8e966ea3243696bdca17a8. Tests construct the expected binding independently from recorded run/source/page/policy constants, rather than trusting the fixture binding. The fixture contains only checkpoint metadata, not credentials or source content. A repository fixture/hash is not independent authentication of current provider state.

The saved live record has zero completed receipts and no pending stage. It is classified as initial, not completed work. Missing fresh authority blocks it. A synthetic host-assertion case may identify SOURCE_PRESERVED as next, but never executes the live job.

## Synthetic fork and actual process restart
A separate run identity, synthetic destination UUID, policy and code revision fork only the initial empty state. No live record is advanced. Tests compose AuditCheckpointTransport, CheckpointAdapter, run_resumable and the read-only decision entrypoint against a temporary file-backed synthetic page.

A subprocess completes the first three stages, saves intent for ANALYZED, writes its synthetic effect and exits abruptly before a receipt. A separate process reads the ordered/hash-linked checkpoint and reports RECONCILE_ONLY. Missing evidence holds without changing calls or checkpoint history. After direct observation of the synthetic effect, another process confirms that pending stage without invoking it again, runs only the remaining three stages, and independently reads completed receipts. A later fresh completed-job process appends nothing and invokes no executor. All seven synthetic stage effects occur exactly once.

Temporary checkpoint writes use file and parent-directory fsync and atomic replacement. Effects use exclusive file creation. This exercises process restart on a surviving host, not loss/replacement of the host/VM, distributed fencing, adversarial file replacement, remote provider persistence or actual source analysis. Seven stage callbacks produce synthetic effects only; arbitrary callback evidence does not authenticate real work.

## Validation and boundaries
Twelve focused tests pass: nine entrypoint cases (including one red/green duplicate-host-binding regression) and three composed tests, including snapshot pinning, malformed/stale bindings, unavailable observation and fresh-process no-replay behavior. Hosted and independent review must bind the final revision before adoption.

No network/provider calls, Notion writes, listeners, schedules, credential or permission changes, pipeline activation or checkpoint promotion. Production remains paused; CP09 is not proved. Rollback is normal reviewed revert preserving prior checkpoint and failure evidence. No automatic resume is installed.

