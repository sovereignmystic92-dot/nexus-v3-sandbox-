# Automatic approval and guarded writes — implementation candidate

This implements parts of [the adopted owner delegation](../OWNER_APPROVAL_POLICY.md).
It does not establish live two-model orchestration, production readiness, CP10
completion, or provider-side fencing. No permission or credential changes are made.

## Coverage

All nine current work workflows receive a preflight before their work or credential use.
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


## Current-main integration — 2026-10-29 draft
PR84 main637404eb9cf67988e4f743acc837e214525407f4 supplies the hardened verifier,
23 approval regressions and unchanged empty trust. This proposal preserves those
files/fixes. No reviewer account is inferred from the author, Chat or Gemini labels.
The trusted-base missing-file prerequisite is resolved on main, but an approval
attempt must now HOLD on empty trust rather than report approval.

The three newer Notion workflows now have proposed preflights before credential
use. Audit access and saved-checkpoint resume-plan remain read-only classifications.
Checkpoint write is classified routine_write, not exempt; its preflight
deliberately HOLDs because no authenticated operation-specific receipt handoff
is provisioned. Adopting this entire PR would therefore block that manual write
probe until separately reviewed authorization wiring exists. Existing confirmation
inputs, protected environment, concurrency and exact-source restrictions remain.

The schema permits consequential workflow classifications, but preflight only
exempts SAFE classifications. It cannot grant approval to routine_write or
production_deployment. No policy trust identities or live authority collector
are added; no model calls, credentials, protections, scheduler changes or automatic
merge are installed. The added coverage is a draft security change, not enforced
protection on current main. This proposal remains unmerged.

Next bounded integration gates:
1. Directly validate final head/current-base code, tests, decoded logs and saved files.
2. Independently review workflow coverage and explicit checkpoint-write HOLD behavior.
3. Establish authentic distinct reviewer accounts and attributable submission paths
   before populating trusted_reviewers; test identities are not enrollment.
4. Review and specifically authorize protected approval enforcement; candidate YAML
   and a required check name do not themselves authenticate an implementation.
5. Wire operation-bound approvals into one permitted adapter with checkpoint intent,
   independent readback and no replay after uncertainty. No blanket connector
   interception, live execution, CP09 resumption or production activation follows.

## Hosted coverage regression and repair
Initial integrated head b023f49194b29ea8fab48bca93b3ad9f33806a86 failed synthetic
run40930557474/job123647533810: 498 cases, one SKIPPED YAML coverage test, fault
checks not attempted. Local host validation had passed because YAML was present.
The no-skip runner requirement is retained. Source coverage now runs explicitly
on exact checkout in a host-only verifier before isolated tests; isolated unit
cases cover policy semantics without skipping. This is source-order evidence,
not proof of environment approval timing or every external operation.
Initial approval run40930557384/job123647532609 fetched trusted base successfully
then returned HOLD/exit2 with empty trust. That is expected refusal, not an
approved review or a repaired approval result.
