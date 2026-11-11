# PR57 trusted-base bootstrap proposal

Status: DRAFT — security-control design only. No activation or merge authorized by this document.

## Observed state and provenance
Repository: sovereignmystic92-dot/nexus-v3-sandbox-.
Inspected main: 515141f30ca57ad79800a6be386f4889e639484f.
PR57 source: 76eeb264281e50b9d85ed31ccc7bff2cbb8a0db3.
Approval workflow: .github/workflows/approval-policy.yml.
Failure: https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/40873258734
The workflow fetches tools/approval_gate.py and tools/approval_policy.json from the event base SHA. Main lacks those files; HTTP 404 stops the job before review verification. This is not an approval result. Existing synthetic/offline success does not resolve this bootstrap prerequisite.

Related proposal: PR82, current-authority evidence handoff. Reuse PR57 contracts rather than create another approval framework.

## Stage A: inactive verifier bootstrap
Prepare a separately scoped draft based on current main containing only the reviewed verifier, deny-by-default policy, focused tests and limitations documentation copied from an exact PR57 revision. Record source blob hashes and compare saved files independently. Do not include workflow preflights, approval workflow, required-check/settings changes or write-adapter activation.

Keep trusted_reviewers empty and production destinations empty until real independent reviewer identities are established. Empty trust must return HOLD before network calls; installation is not approval capability. The bootstrap uses existing applicable governance and native checks, plus specific security-control review/authorization. It cannot certify itself using the uninstalled proposed approval workflow. If an existing native gate blocks it, stop; no bypass, forged PASS, temporary exemption, candidate-source fallback or protection change.

Before adoption review inspect all verifier failure paths, exact policy types/schema, API endpoint/proxy/redirect behavior, response size and pagination, stale or dismissed approvals, author exclusion, distinct sessions/identities, final PR context recheck and evidence applicability. Candidate code must not run with credentials. An evidence URL alone is not verification of its content. Passing fixtures do not authenticate reviewers.

Validate current head/base or exact merge candidate, review code and decoded logs, save premerge checkpoint and rollback plan, independently read back, and recheck native gates. Stage A merge requires appropriate specific security-control authorization; routine standing approval is not sufficient. Observe postmerge main checks and independently fetch exact verifier/policy bytes before calling installation verified.

## Stage B: identity enrollment and activation review
No eligible reviewer identities are currently established in this proposal. Do not invent logins, map the PR author to two reviewers, label the existing synthetic Gemini smoke test an independent reviewer, or copy model/session assertions as authentication.

For each proposed identity, supply:
- exact GitHub account ID/login, verified operator/service control and least-privilege submission path;
- review provider/model provenance, distinct session identity and isolation procedure;
- exact policy/source revision, permitted operation/destination and immutable request binding;
- a native current-head APPROVED receipt submitted by that identity, with independently inspected code/tests/logs and limitations;
- revocation, dismissed/stale review and material head/base/context-change handling.

Review the concrete evidence and specifically authorize trust-policy population and control activation through applicable governance. Provisioning accounts, credentials, permissions, protections, services or model-review orchestration remains outside this task. Two subagent sessions under the same GitHub account do not satisfy two distinct trusted identities. Do not falsify prior_conclusions_seen.

Once Stage A is actually present on trusted main, rebase/integrate PR57 without discarding intended changes. Revalidate changed code and renew affected reviews. Stage B must fetch verifier and policy from the exact trusted base, never from the candidate when the base fetch fails. Verify downloaded bytes against the reviewed source manifest. Require actual approval-evidence execution with exact head/base/run/attempt bindings; a successful fetch with empty trust must still HOLD. Only authentic qualifying receipts may produce REVIEW_RECEIPTS_ACCEPTED.

PR57 modifies six earlier workflows; three newer Notion workflows currently lack its preflight. Inventory all current workflows before activation and propose coverage changes separately. Do not claim blanket enforcement from partial coverage. Candidate-controlled YAML/check names alone do not authenticate an unbypassable implementation; trusted required-workflow or equivalent enforcement requires separately reviewed repository controls. No auto-merge or setting changes are included.

## Required acceptance evidence for this proposal's implementation
1. Inactive-bootstrap diff contains no workflow/control activation; source provenance and independent saved-code hashes match.
2. Missing verifier fails closed; no candidate fallback. Empty/malformed trust, stale/dismissed/untrusted/self approval, context drift, incomplete pagination and API failure hold.
3. Two genuine independent identities and sessions are verified before enrollment; no identity is inferred from test data.
4. Trusted-base files match reviewed installation; full current-base tests and native gates pass.
5. Readiness, authority, successful dispatch and independent effect readback remain separate judgments.
6. No production activation, CP09/fencing claim, score promotion, credential/permission change or automatic provider writes.

## Rollback and next step
Before any authorized merge, record exact PR/head/base, source hashes, tests/reviews, intended inactive sandbox scope, authorization and normal reviewed revert plan in the Foundation Audit and fetch it independently. Revert any adopted bootstrap through a normal reviewed revert; preserve failures and checkpoints. No destructive cleanup.

Next finite work item: prepare and review the inactive Stage A extraction only. Stage B remains BLOCKED pending verified reviewer identities and specific security-control authorization. This document does not itself request or grant broad permissions.
