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
malformed sequence, wrong run and uncertain append without duplicate. They do not
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
