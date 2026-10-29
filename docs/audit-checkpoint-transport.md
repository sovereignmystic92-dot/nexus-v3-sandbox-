# Audit checkpoint transport — opt-in proposal

The host injects existing connector fetch/append calls. This library does not
obtain credentials, call Notion HTTP APIs or install a runtime. One explicitly
enrolled audit job is selected by exact page UUID and immutable binding. Enrollment
is a sequence-zero NXS_CHECKPOINT_V1 JSON event containing the codec's initial
checkpoint. Missing enrollment holds; this transport never silently creates it.

Every event includes run/page identity, contiguous sequence, previous-event digest
and strict checkpoint JSON. Complete page retrieval is required. Duplicate or
conflicting matching events hold. Saving re-fetches the page, rejects observed
drift, appends one generated event and separately fetches it. Lost acknowledgment
invalidates instance write permission; a fresh read can observe the effect without
repeating append. Pipeline action uncertainty remains observation-only.
Enrollment must be empty with no pending intent. Every observed and proposed
transition preserves the receipt prefix and alternates next-stage intent with
its matching result; visible regression, skipped intent and post-completion
changes hold. Malformed or unterminated JSON blocks anywhere on the page hold
conservatively, even if apparently unrelated; escaped markers cannot hide them.

Seven local fake-connector tests cover all seven stages, fourteen intent/result
checkpoints, completed repetition, missing/duplicate/incomplete enrollment,
malformed sequence, wrong run and uncertain append without duplicate.
Additional regressions cover escaped malformed events, invalid enrollment and
visible chain regression/skipped intent. These tests do not
prove a real connector transport or live provider. Page JSON markers are not
authentication. Hash chaining detects observed inconsistency, not malicious
rewriting or whole-history rollback. Preflight comparison is not atomic CAS.
One trusted worker only; no concurrent takeover. Raw source content must not be
copied into checkpoint custody as executable event records.

Before a live test, independently bind the existing connector and authorized
runtime, explicitly enroll a bounded job on the approved Foundation Audit, prove
complete fetch/selector behavior and retain exact event/readback evidence. Tool
availability alone does not authenticate identity. No new credentials, permission,
service, workflow or production activation is part of this proposal. External
transport activation/security review remains separate from library adoption.


## Shared-reader integration — 2026-10-28

The current proposal brings PR63's transport unchanged onto main
`9713d0be075afc94bf457b3c9126074f8adb7d96`, which includes the adopted
NotionCheckpointAPI and shared table inventory reader. The host can inject
`api.fetch_page` and `api.append_text` into AuditCheckpointTransport, then use
CheckpointAdapter to bind the transport to run_resumable. This is library wiring;
no host runtime, enrollment, credentials, workflow or live operation is installed.

Six additional synthetic REST-shaped integration tests exercise this exact
composition: all seven stages and fourteen intent/result appends with separate
readbacks, fresh completed resume without replay, disabled writes, wrong-parent
table rows, exhausted shared pagination budget, lost append acknowledgment, and
corrupted append readback. The fixture places enrollment after a paginated table.
Its PATCH calls modify in-memory fixtures only. No network or provider writes occur.

Local validation: 395 unit tests passed, including eight transport tests
and six new integration tests. Workflow inventory hashes match. Hosted validation
and final independent reviewer dispositions must be recorded separately before
adoption; local success alone does not authorize merge. The two AI reviewers use
separate sessions of the same inherited model configuration; this supplies session
independence, not cross-model-family independence.

The library still requires a trusted exclusive worker, authenticated host callbacks,
complete bounded observations and explicit empty enrollment. It does not establish
remote CAS/fencing, authenticated history, rollback detection, long-term durability,
live write capability or production readiness. Live writes, bridge activation,
production changes and CP09 remain outside the current standing approval.

Independent review found that Python accepted NaN/Infinity/-Infinity in unrelated
JSON blocks. A new raw-block regression failed all three subcases before the fix;
the transport now rejects nonfinite constants during decoding. The revised full
local suite passes 395 tests. Hosted validation and publication are pending.

Final local review dispositions: reviewer sessions /root/transport_review_a and
/root/transport_review_b both APPROVED the synthetic-only library scope. Each
recorded an independent initial review before comparison. B found the nonfinite
JSON defect; A initially found no material defect. Both renewed their reviews
after the fix and disclosed exposure to the compared finding. A reran all 395
unit tests; B reran 14 focused transport/integration tests plus 77 Notion tests.
Exact runtime model identities were not independently observable.

Final SHA-256 review bindings:
- transport: 1556b0d19fadd90b50e650b195cfbfcc3bcdcaa8c9816c696b0695b13ef8dce7
- transport tests: ba9bc3793e431319bc5fd185cc9f765bb7f74e942b0cff1961bf2eef98eb9d73
- integration tests: 700e909fc8f9e4c64a4f6a7f9cf2aae24d9f16528d1705a868369acb987fed28

Publication was rejected by automatic approval review: the review did not accept
transcript-carried authorization for exporting new code to the GitHub destination.
No workaround or alternate write path was attempted. No hosted integration result,
new PR, merge, Notion audit write or live activation is claimed. Owner confirmation
of the concrete destination/payload is needed before retrying publication.
