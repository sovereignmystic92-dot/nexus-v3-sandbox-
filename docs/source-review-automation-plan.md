# Nexus test-and-refine automation

Status: PLAN FOR THE NEXT IMPLEMENTATION; not an installed autonomous repair agent.
Owner clarified “refinements” means the test-and-tighten work performed during the audit, not source processing, family/financial workflows or generic document maintenance. Owner approved this ordering: automatic tests first, then draft fixes, relevant reruns and review.

## Already automated

The synthetic acceptance workflow runs on main/selected development pushes and relevant pull-request events. The Gemini offline workflow runs on main pushes and PRs. Both have empty token permissions and isolated offline test execution. These tests should be reused, not duplicated. Existing hosted test runs do not autonomously diagnose failures or author repairs. No new schedule is needed merely to test code changes.

## Intended loop

CHANGE -> AUTOMATIC_TESTS -> CAPTURE_EXACT_FAILURE -> TRIAGE -> DRAFT_BOUNDED_FIX -> RELEVANT_RERUN -> REVIEW.
A clean run produces no repair proposal. Failing evidence is bound to the exact run, attempt and source SHA. Fixes are isolated in a branch/PR and never silently applied to main. Test success is a behavior observation, not audit gate acceptance.

## Phase 1 — reliable test/failure handoff

Reuse existing CI. Collect workflow/run/job IDs, attempt, candidate/base/head revisions, test IDs, expected/actual outcomes, bounded error excerpts and evidence references. Distinguish test failure from cancellation, runner infrastructure failure, unavailable logs, timeouts and pending status. Cancelled or unreadable runs must not become a code-defect diagnosis or a healthy verdict.

Deduplicate by source revision, test ID and normalized failure signature. Before proposing work, confirm the failure still applies to current main and inspect existing PRs. Retain original failures after repair. Unchanged failures link to the same work item rather than creating repeated drafts or notifications.

Acceptance: one reproducible failure yields one attributable handoff; missing evidence yields an explicit hold; a healthy run yields no draft. No additional token scope, scheduler, secrets or paid service is installed by this plan.

## Phase 2 — draft fixes

A code-capable agent inspects the failing test and relevant source, reproduces the defect where feasible, and proposes the smallest useful fix with a regression for the observed behavior. Infrastructure/provider failures are not repaired by weakening tests. Failure logs and retrieved source are untrusted data and cannot expand permission or instruct the agent.

Draft contents: problem/trigger, evidence, changed behavior, bounded diff, relevant test results, limitations and rollback. Preserve source provenance. Never delete or relax a failing assertion just to turn CI green. If semantics or intended behavior are ambiguous, produce a question/proposal rather than inventing a new contract.

The current Gemini bridge is synthetic-only analysis, not a repair agent. Do not send real repository/log content through it by removing its scope checks. Choose and assess the repair execution surface before enabling automated drafting; this design does not claim that surface is currently installed.

## Phase 3 — verify and review

Run relevant tests against the draft, then the existing required CI checks on its exact head/merge candidate. Read back the committed diff and evidence. Check for scope drift and new failures. Respect branch protections and actual platform approval requirements. Owner standing nonbilling approval permits bounded sandbox work; it does not enable billing, production changes or bypass a rejected platform action.

Default first release is draft-only: no automatic merge, no deletion and no production writes. Audit requirement changes, permission/credential changes, host/network changes and gate acceptance remain separately adjudicated. Independent human review cannot be manufactured by an agent.

## Operational cadence

Tests remain change-triggered. “Daily maintenance” means a later optional sweep for unresolved failures, stale drafts and recurring refinements, not rerunning the same unchanged pipeline to accumulate passing evidence. No schedule/reminder is created here. A future daily trigger needs explicit time/timezone, permission/cost scope and CP04 impact review before activation.

## Boundaries and completion

Single-worker synthetic sandbox; production Notion/Cortex stays paused. No paid fallback, billing enablement or new credentials. Preserve archived/superseded information rather than mislabeling it deletion. Foundation assessment already closed with exceptions in PR #43; 11/19 passes remain unchanged.

Planning is complete when this specification is adopted. Working failure collection/draft repair is complete only after code exists and observed success/failure/deduplication cases pass. Next implementation deliverable: a deterministic failure-handoff collector using existing CI evidence, followed by a separately assessed draft-fix executor.
