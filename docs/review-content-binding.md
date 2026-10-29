# Review artifact binding — inactive offline proposal

Purpose: bind review content to exact sandbox operation context while preserving
the separate identity/authentication gate. This does not amend PR57, enroll an
identity or replace the existing native approval receipt contract.

## Scope and existing contracts
Base main637404eb9cf67988e4f743acc837e214525407f4 already contains the hardened
tools/approval_gate.py. The new tools/review_binding.py reuses its strict JSON
decoder, Hold and exact-SHA validation. No duplicate credential/trust store,
provider transport, scheduler, write journal or approval service is introduced.
No workflow changes or live calls occur.

Required context: repository, positive PR number, exact head/base/tested-candidate
SHA, routine_write operation, exact destination, complete write-intent SHA-256 and
policy revision. The host must establish candidate ancestry and actual relevant
test evidence; syntactically valid SHAs do not prove either.

Required source: store (cortex/github), exact record ID and record revision.
claimed_agent and session_id preserve claims, not authenticated writer identity.
The packet includes exact UTF-8 review-body SHA-256 and a bounded map of observed
evidence references/digests. No provider-sensitive review bodies are printed or
stored by this library. Canonical wire digest binds all packet fields.

bind returns canonical wire text plus digest. verify requires independently
retained expected context, source, digest, agent/session and freshly observed
review body/evidence. Rejecting canonical text changes is intentional. Old record
revisions, review/evidence changes, wrong head/base/candidate/destination/intent,
extra fields, duplicate JSON fields, Boolean schema version, NaN/Infinity and
oversized packets hold. A fresh process can verify a saved synthetic snapshot.

## Identity boundary
A match returns only:
- status: BOUND_UNAUTHENTICATED
- approval_granted: false
- identity_status: UNVERIFIED

There is no function that returns authenticated approval. No caller should treat
this content-match result as an approval_gate.authorize receipt. A digest carried
beside its own packet is not independent custody; an attacker able to replace both
can manufacture a new binding. This library cannot detect whole-history rollback
if the host accepts the rolled-back expected snapshot.

The host must independently verify actual writer/connector/service identity,
record metadata/history, access scope, current status/revocation and genuinely
independent sessions. Content fields such as source_agent:Gemini, model names,
Cortex module owner, screenshots or user reposts are not that authentication.
Evidence hashes do not prove that evidence is true, relevant or complete.
Review text may contain arbitrary claims; matching preserves them without
endorsing their verdict. No single-worker/provider CAS/fencing assurance follows.

## Cortex handoff
The user-authorized read-only search found Gemini-attributed research handoff
NEXUS-HANDOFF-SITH-01 in module_01m4j4g8q8e6z5zrpzxw5yvtdv. That historical
research record lacks this operation's exact PR/head/base/intent/review context
and must not be converted into approval. This prototype does not read it again,
write Cortex or claim authenticated Gemini authorship.

A future reviewed host adapter would fetch exact source metadata and review
content independently, validate the authenticated submitting principal against an
enrolled trust mapping, then persist/read back the immutable binding through an
already authorized journal. No trust mapping or authenticated adapter is installed.
Existing PR57's two-native-reviewer requirement is unchanged; using Cortex as an
alternative approval identity source requires a separate reviewed proposal and
specific authorization, not merely this content-binding utility.

## Validation and adoption
10 focused local offline tests pass, including tamper/recomputed-digest rejection
against an external expected snapshot, context/source/evidence/session drift,
malformed inputs, old research-handoff rejection and fresh-process saved readback.
The first fresh-process harness failed because the socket stub preceded urllib/ssl
import; it was corrected to prohibit sockets after module imports, then passed.
No provider requests were made by these tests. Hosted and independent review
results must be recorded separately; primary validation is not independent review.

Remain draft/inactive pending exact-source/current-base review and native checks.
No merge, credentials/permissions/protection/settings/schedule change, workflow
activation, production activation, CP09 resumption or checkpoint promotion.
Rollback after any separately authorized adoption: normal reviewed revert,
preserving review/failure evidence. No destructive cleanup.
