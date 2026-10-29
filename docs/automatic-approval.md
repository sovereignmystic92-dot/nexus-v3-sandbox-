# Automatic approval and guarded writes — implementation candidate

This implements parts of [the adopted owner delegation](../OWNER_APPROVAL_POLICY.md).
It does not establish live two-model orchestration, production readiness, CP10
completion, or provider-side fencing. No permission or credential changes are made.

## Coverage

All six existing workflows receive a preflight before their work or credential use.
The reviewed policy classifies offline validation, read-only probes, and the existing
manually confirmed synthetic Gemini pilot as exempt from two-AI approval. Existing
confirmation inputs, environment controls, and secret restrictions remain in force.
An unknown workflow classification holds. Workflow byte inventory is updated alongside
these changes; it does not inspect provider settings or prevent an administrator bypass.

The new `Independent AI approval evidence` workflow reacts to PR changes and submitted,
edited, or dismissed reviews. It fetches guard code and configuration from the event's
base SHA, not the proposed PR source. It checks native GitHub approvals from configured
trusted reviewer logins, excluding the PR author. Two distinct sessions and two distinct
reviewer identities are required. Current head SHA, operation, destination, request hash,
model/provider identity, independence attestation, evidence references, limitations, and
no unresolved findings must match. Dismissals, changes requested, stale revisions,
incomplete pagination, malformed JSON, untrusted identities and API failure hold.

The guard performs bounded unauthenticated public API reads with no redirects, no
tokens, no model calls, no auto-merge, and no mutation permissions. Public rate limits
can cause a hold. Review evidence references and model/independence statements are
trusted-reviewer attestations, not provider-signed proof or automatically reproduced
test evidence. A GitHub run URL is not proof that its results are passing or applicable;
the reviewers must inspect and validate evidence before signing. Technical readiness
remains a separate prerequisite. Reviews are visible on GitHub; attesting no prior
exposure is procedural assurance, not enforced isolation between models.

## Actual activation blockers

1. `tools/approval_policy.json` intentionally has no trusted reviewer identities.
   None have been verified as independent automated AI reviewers. Therefore delegated
   approval holds. Do not populate it with invented accounts or model labels.
2. The existing Gemini integration is a manually confirmed synthetic pilot, not a code
   reviewer. Automatic Gemini and ChatGPT review dispatch and attributable submissions
   are not provisioned by this implementation.
3. GitHub must enforce the approval check through trusted repository controls before
   it can be called an unbypassable merge boundary. Workflow YAML alone does not set
   branch protection. A candidate can edit a candidate-controlled workflow; requiring
   a check name alone does not authenticate its implementation. Use trusted required
   workflows or an equivalent protected approval service before production reliance.
   First adoption cannot fetch guard files from a base revision that lacks them: its
   approval-evidence job will hold as a bootstrap condition, not an AI-approved result.
4. No production deployment workflow exists. Production destinations remain empty.
5. Direct Notion and Cortex connector calls are not intercepted by repository code.
   Their write adapters must be wired to the guard and existing readiness checks.
   Actual provider stale-write protection remains unresolved under CP09.

Provisioning identities, permissions, credentials, or repository administration may
require the separately reserved owner approval. This candidate neither makes those
changes nor asks the owner to approve hypothetical changes in advance.

## Structured native review receipt

The entire native GitHub APPROVED review body is a JSON object containing exactly:
`policy_version`, `revision`, `operation`, `destination`, `request_sha256`,
`session_id`, `model`, `provider`, `verdict`, `evidence`, `findings`,
`prior_conclusions_seen`, and `limitations`.

`verdict` must be `PASS`, `findings` must be empty after resolution,
`prior_conclusions_seen` must be false, and evidence must reference this repository's
run URLs or exact-revision files. Record initial findings independently before
comparison. Resolve issues, then independently review the final revision. Any exposure
to the other's conclusions must be disclosed rather than falsely attested as blind.
If that condition cannot be met, the automatic guard holds; obtain genuinely fresh
reviewers or revise the procedure explicitly instead of changing a boolean.

For a GitHub main update, the default request hash is SHA-256 of compact JSON
`[revision, operation, destination]`. For adapter writes, provide `--request-sha256`
equal to the entire immutable write-intent hash described below. A review author is
not allowed to approve their own PR. The PR must be open, target main, and use this
repository for both head and base.

## Guarded write implementation

`ApprovedWriteBoundary` is an opt-in, single-worker reference. Trusted adapter callbacks
must supply authorization, exact-destination reads, and writes. Its immutable intent
binds code revision, `routine_write`, destination, expected baseline hash, and payload
hash. The authorization callback must return a current guard receipt for that exact
intent and check all additional applicable readiness requirements. A fabricated PASS
dictionary or unverified model statement is not a valid production authorizer.

Before mutation it rechecks the destination baseline and commits a SQLite DISPATCHING
intent. It invokes the write once and separately reads back the intended content.
Failure, lost reply, or mismatch leaves an uncertain outcome. Reopening with the same
request reconciles by reading, never by retrying the write. Reusing the request ID for
a changed intent holds. Journal entries retain hashes and state, not raw payloads.

This does not authenticate callbacks, make provider reads independent of the operator,
provide remote CAS, survive complete journal loss, prove retention deletion, or enforce
atomicity across a provider. New requests after an uncertain result require explicit
reconciliation; changing an ID must not be used to bypass the hold. Keep the single-worker
restriction. Destructive operations must not be mislabeled as routine writes.

## Validation and adoption

Targeted local tests cover receipt binding, stale/dismissed review rejection, absent
trust configuration, unsafe operations, bounded pagination, preflight ordering,
durable pre-dispatch intent, baseline mismatch, independent read-back, and lost-reply
reconciliation without repeated writes. These tests use synthetic fixtures and mock
provider callbacks. Hosted tests and review status are recorded in the PR.

No real Notion/Cortex mutation or live AI review request is made by these tests.
This implementation remains a draft until independently reviewed under the adopted
policy or separately directed by the owner. Existing checkpoint scores are unchanged.


## PR-context recheck repair (draft)

The final PR observation now rejects changes to the base SHA/ref/repository, head SHA/repository, author or open state, including missing/malformed context. This closes an observed hole where a base change during the approval check could still return accepted receipts. Four new regression tests include the actual CLI path with a changed base after initial authorization; the original returned exit 0 and the repaired version returns HOLD/exit 2. Twelve existing guard tests also pass locally. These are mocked observations, not authenticated live-provider assurance. Review receipts can still change after their observation; there is no atomic provider-side approval/dispatch boundary or remote fencing. Empty trusted-reviewer configuration, bootstrap and all previously documented activation blockers remain. No workflow, policy identity or permission changes accompany this repair; security-control proposal remains draft.
