# Opt-in supervised journal custody

Status: offline implementation for independent review. No live storage port,
provider identity, grants, protected checkpoint service or dispatcher is installed.
This does not approve a live CSF operation or close CP09.

The existing `provider_custody.CustodyLedger` records a different Chat-adapter
observation contract. It does not snapshot the native supervised execution
journal. This module adds that specific missing barrier without a second source
archive, processing engine, state machine or provider writer.

`execute_custodied_supervised` delegates to mandatory-gated `execute_supervised`.
`execute_custodied_connected` composes the existing connected entrypoint and
preserves its separate retained-receipt gate. Neither silently redirects other
callers. Both require the unchanged complete analysis gate; a blocked assessment
still fails before journal initialization or provider requests.

## Host ports and authority

Construct `JournalCustody(key, expected_binding(arguments), retain=..., read=...,
head=..., cas=...)`. The caller must retain its stable key-to-native-journal
mapping and allocate distinct keys, paths and output names for each consumer.
Changing a mission/work key cannot authorize replacing an uncertain transaction.

- `retain(bytes) -> reference`: retain an immutable private object. Its reference
  is nonempty, at most 512 characters, and has no surrounding whitespace.
- `read(reference) -> bytes`: freshly retrieve the exact durable object. No
  echoing cached arguments as independent readback. Access errors must raise.
- `head(key) -> {generation, reference, sha256} | None`: freshly retrieve the
  protected authoritative pointer. None means confirmed absence, never an error,
  missing local mirror or inaccessible record.
- `cas(key, expected_head, new_head) -> bool`: atomically compare the entire old
  head and advance to the new head. Exactly True is accepted, followed by fresh
  pointer and object readbacks. A read-then-write implementation is insufficient.

The ports are trusted host obligations, not authentication established by Python
callbacks. The host must verify principal, account/parent/destination grants,
runtime code/policy revisions, full fresh source pagination and applicable
operation approvals before using a live provider request port. This library has
no connector implementation and grants no permission. There is no default store.

Journal bindings can contain original transcript chunks. Custody snapshots and
references therefore belong in authorized **private** evidence storage, never
the public repository, public CI logs or untrusted artifacts. Only synthetic
fixtures are used in the tests. Journal snapshots are limited to 16 MiB.

## Ordering and failure behavior

1. `initialize=True` is an explicit new-transaction bootstrap. Both the local
   journal and authoritative head must be absent; old/lost work must be
   reconciled, never bootstrapped with a fresh key. Default invocation requires
   an existing bound local journal and retained head.
2. The native host holds its local flock. At the first request, snapshot its
   committed journal with SQLite backup (including committed WAL pages). Check
   integrity, exact native binding, singleton state and module identity. Retain
   the envelope, independently read it, atomically advance the protected pointer,
   and freshly read back pointer and journal before any provider request proceeds.
3. Native FULL-synchronous INTENT is committed before `cortex_create`. The wrapper
   repeats the retention/readback/CAS barrier at this callback and refuses to
   dispatch without a matching INTENT. Failed retention, corrupt content, CAS
   conflict or pointer mismatch prevents the provider create. An uncertain CAS
   is a reconciliation hold, not a retry instruction; orphan immutable objects
   may remain and are not automatically deleted.
4. After the native result, checkpoint the current journal again. A failure here
   does not undo a possible provider effect or claim success. The retained INTENT
   stays authoritative until explicit reconciliation; never rerun the create.
5. Retained states cannot regress, and an already verified module ID cannot
   change. The full binding includes prepared source, exact output hash, owner
   and analysis evidence hash. These are native bindings, not new authority.

`custody.restore(missing_path)` validates the authoritative head, exact object
hash, envelope/key/binding, SQLite integrity and state, then exclusively creates
and fsyncs the journal. Existing files and symlinks are refused. A partial local
restore failure leaves reconciliation work; the caller must not silently
overwrite it. Restore never grants create permission. Reopen through the same
guarded host, preferably `allow_create=False`: retained INTENT permits read-only
reconciliation of an existing exact output, but absence cannot release intent
or authorize a replacement create. Preserve any differing local copy for
operator reconciliation; this module does not overwrite it with a snapshot.

## Remaining limits

This is one cooperating worker using the native allocated journal lock. CAS
protects pointer advancement under the trusted store contract. It does **not**
fence a stale dispatcher at the provider's mutation boundary; a race can still
occur after the last pointer observation. Concurrent workers, distributed
takeover, whole-store rollback/deletion and power/device-loss guarantees are
excluded. No checkpoint service is implemented or certified. These exclusions
cannot be used to claim full operational approval; a live review must expressly
accept the bounded single-worker contract or require additional controls.

Returned `JOURNAL_READBACK_MATCHED` describes only journal custody observations.
The connected result may still be PENDING_RECEIPT or BLOCKED. Durable execution
receipts, their independent fetch and the final connected persistence milestone
remain separate obligations. No caller may infer overall completion from the
custody status. Existing code/analytical approvals do not approve these changes.

## Validation and rollback

Run `PYTHONPATH=src python -m unittest discover -s tests/unit -p
'test_supervised_journal_custody.py' -v` as one command. Synthetic cases include
pre-create storage/readback/CAS failure, protected-pointer conflict, lost pointer,
wrong binding/corrupt restore, no overwrite, committed WAL intent, uncertain
committed/absent outcomes, final checkpoint failure and a separate process that
exits abruptly after a synthetic effect; restoration makes no second create.
The connected integration case still requires its separate durable receipt.

Also run the supervised, connected and quality-host suites. These are local
SQLite/subprocess and synthetic-port checks, not authenticated storage/provider,
distributed fencing, host power loss or independent review evidence.

Author validation on this change: 21 custody cases and the full local unit
discovery passed (1,145 tests total), using `PYTHONPATH=src python -m unittest
discover -s tests/unit -p 'test_*.py' -q`. No hosted CI result, independently
reviewed verdict, authenticated custody port or live provider write is inferred.

## Independent static review follow-up

The owner relayed a Gemini static review of revision
`afa82b93bae57810da5cb0116190dca8d8c74309`: APPROVE_OFFLINE_CODE, with zero
reviewer-executed tests and no hosted/live acceptance. One Medium coverage gap
and three Low hardening findings were recorded. This follow-up adds retained
connected-receipt re-entry coverage (VERIFIED generation 3 after first create,
generation 5 after read-only re-entry, one create total); creates restored files
atomically with mode 0600; copies both CAS arguments; and rejects nonfinite
JSON constants during parsing. These changes require renewed exact-revision
review. The documented provider-boundary race and single-worker scope remain.

Rollback removes the opt-in module/tests/document; retain actual immutable
objects, authoritative heads, local journals and uncertain intents. Existing
host APIs and workflows are unchanged.
