# Nexus refinement and daily maintenance automation

Status: IMPLEMENTATION PLAN, NOT DEPLOYED. This replaces the initial source-to-draft proposal based on the owner's clarification: prioritize ongoing refinements and daily maintenance, not a new source-processing pipeline.

Foundation assessment remains COMPLETE_WITH_DOCUMENTED_EXCEPTIONS. Full acceptance BLOCKED; production stays paused. Checkpoint score remains 11/19. No billing enablement or paid fallback.

## Purpose

Make ongoing upkeep less repetitive: inspect the current sandbox baseline, verify evidence and active policy, identify regressions or unfinished refinements, and produce one concise maintenance brief with actionable proposals. Prioritize useful behavior and recurring problems rather than repeated demonstrations or tests solely to increase a score.

## Daily maintenance contract

| Stage | Work | Result |
| --- | --- | --- |
| Establish baseline | Read exact current main revision, adopted closure/register and relevant new changes | Revision-bound scope and exception list |
| Check health | Inspect latest checks, open/failed/stale PRs, workflow inventory and evidence references | Confirmed healthy, failed, stale or unavailable observations |
| Review consistency | Compare current statuses with cited evidence; identify outdated proposed/pending wording and missing references | Specific discrepancies with provenance, not inferred repairs |
| Handle lifecycle | Flag old drafts/superseded artifacts, preserve source/history and current/noncurrent distinctions | Archival proposals; no bulk archive or deletion |
| Review refinements | Compare recurring issues and user-approved improvement backlog with current implementation | Ranked bounded refinement candidates with expected user benefit |
| Report | Produce one dated maintenance brief | Changes since prior baseline, findings, completed checks, blockers and next actions |

A daily cycle is the intended operating cadence. Initial implementation is manually launched; no schedule or reminder is installed by this plan. Before enabling a recurring trigger, record its timezone/time, execution surface, permission boundary and cost controls, and review CP04 for the changed trigger. “Daily” must not be reported as active until the scheduler exists and a run is observed.

## Refinement workflow

DETECT -> VERIFY -> CLASSIFY -> PROPOSE -> IMPLEMENT_IN_SANDBOX -> TEST -> READBACK -> RECORD.

Read-only findings can be collected without changing operational records. For a bounded sandbox refinement under the owner's standing nonbilling approval, prepare an isolated branch/PR, retain the problem and expected behavior, run relevant checks and independently read back committed changes. Adopt only after required checks and applicable repository approval rules pass. Any actual platform approval remains mandatory. Report intended, attempted and confirmed actions separately.

Recurring findings should inform a concrete improvement; they must not silently rewrite constitutional authority, definitions, accepted source material or user intent. Preserve prior results, rejected hypotheses and source provenance. Source ingestion/research synthesis is a separate future automation, not the purpose of this first maintenance release.

## Maintenance brief contents

- Exact assessed revision and previous baseline, if available; without a previous baseline, report initialization rather than inventing a diff.
- Verified changes and healthy/failed/unavailable checks.
- Specific drift, incomplete refinement or archival candidate, with supporting record.
- Proposed action and user benefit; severity and confidence.
- Actual actions taken, test results and independent readback.
- Exceptions/deferred work and whether a reopening trigger actually occurred.
- Next useful task and any genuinely required approval or missing information.

No-findings is a valid result. Retrieval failures must be visible; missing access must not become “healthy.” Notifications should be actionable and avoid repeating unchanged deferrals.

## Boundaries

Current execution stays single-worker and synthetic sandbox only. No unattended production Notion/Cortex writes, bulk changes, new credentials, new accounts, activation, paid services or deletion. Archiving/superseding is the interim preservation policy, not proof of erasure. Existing deferred requirements stay unpassed; daily maintenance cannot declare full foundation acceptance or independent human review.

A source/status/reference anomaly is a finding first. Changed checkpoint status requires evidence meeting its full adopted requirement and an attributable decision. Host loss, provider grants, effective identity, fencing and independent review cannot be “fixed” through documentation or a passing local test.

## Implementation order

1. Read-only baseline collector for repository revision, checks, open PRs and current register.
2. Deterministic maintenance findings with exact evidence references and explicit unavailable/stale states.
3. Persistent per-run brief and baseline comparison, using a bounded approved destination and preserving history.
4. Refinement queue with deduplication and user-value prioritization; no repeated unchanged alerts.
5. Reviewable sandbox change preparation and outcome recording under existing approvals.
6. Manual pilot against actual repository observations; inspect whether the brief helps the owner choose useful work.
7. Only then enable an explicitly configured daily trigger. Reassess changed permissions/network/trigger scope first.

## Acceptance cases

| Case | Required behavior |
| --- | --- |
| Healthy unchanged baseline | Concise no-action result without reopening deferred gates |
| Failed check or broken reference | Attributable finding, exact revision, bounded next action |
| Connector unavailable | Explicit incomplete assessment, never a healthy verdict |
| Stale historical wording | Proposed correction tied to current evidence, historical provenance preserved |
| Repeated finding | Same tracked item, no duplicate issue/PR/notification |
| Proposed refinement | User benefit, scope, tests and rollback recorded before adoption |
| Unauthorized/paid/production action | Hold without attempted mutation or paid fallback |
| Archived/superseded item | Preserve provenance; do not call it deleted |
| New exception trigger | Flag only the affected checkpoint for reassessment; no automatic pass |
| Interrupted run | Resume from confirmed baseline, no duplicate changes or invented completion |

This plan is established when adopted; working automation is established only after implementation and observed manual operation. A later scheduled run requires separate configuration and verification. No scheduled task, live API call or runtime behavior is installed by this document.
