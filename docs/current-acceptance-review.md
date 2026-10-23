# Current acceptance review and merge order — 2026-10-22

This review supersedes older status summaries for the reviewed Cortex branch. The C08 follow-through below updates the CI finding; the tables retain the original reviewed snapshot. Earlier test counts and pending-host statements in historical documents describe earlier revisions. This is an author assessment, not independent human review or approval to merge. Notion remains authoritative; its integration remains paused. Production activation and canonical promotion are outside this review.

## Reviewed revisions and evidence

| Item | Current reviewed state | Observed evidence |
| --- | --- | --- |
| Main | `949e635ed75d919f481d88648fefded37a7d0ddd` | Previously merged synthetic coordinator baseline |
| PR #2 | Draft; open; base main; head `f2c981f761ac1088e78c5379148d82d24f7679aa` | [Run 39857370613](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39857370613), tested source `e8df5490c4d5edb7893c681cf0f9d383bcf3ee12`: 32 tests including four mission cases; four separately counted bounded faults |
| PR #4 | Draft; open; base mission-scenarios; reviewed head `bcfe49f996a7261e8d38a482a2622a6b3a24fdab` | [Run 39881697563](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39881697563), tested source `9aeb79bc3d972c5dc2f11a8e08dda8e1743904d9`: 52 tests including 20 Cortex adapter/bridge cases and four mission cases; four separately counted bounded coordinator faults |
| PR #3 | Draft; open; base mission-scenarios; head `db84ec6961528c5b1a080e0c42b5ef56f0781c9e`; PAUSED | [Run 39860541073](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39860541073) is successful at `24563691b33eff348ded092e63e1c6ee82155d1f`; that evidence does not resume or approve the Notion integration |
| C05 live probe | Creation, uncertain-create reconciliation and actual Python restart observed | Three creates in the first process; zero writes in the second; same IDs/version 1 at that time; exact four-module/three-edge Flash |
| C06 live probe | One update and stale target preservation observed | Same registry ID, v1→v2; unrelated metadata preserved; exact repeat made no write; stale v1 request blocked and v2 preserved |

The three hosted run statuses were re-read from GitHub as completed/successful. Git tree IDs for `src`, `tests`, `tools` and `.github` match exactly between the PR #4 hosted-tested source and its reviewed head. Subsequent changes through this review are documentation/evidence only. Live probe code is explicitly stored under docs and does not register an automatic callback. C05/C06 evidence issues were re-read as done. These are distinct forms of evidence; live probes are not additions to the 52-test count.

GitHub reports PRs #2, #3 and #4 mergeable against their current bases. That reports Git compatibility only. No submitted GitHub reviews were returned for PR #2 or PR #4; review outside GitHub was not assessed.

## Remaining acceptance gates

| Control or capability | Evidence established in declared scope | Remaining limit / disposition |
| --- | --- | --- |
| C1 host/filesystem isolation | Hosted offline runner boundary probes, read-only source, bounded resources and disposable storage | Trust in GitHub-hosted VM/engine and shared kernel; not a universal sandbox guarantee |
| C2 test identity and grants | Offline nonroot UID and explicit container configuration; live Cortex owner metadata observed | No independently audited complete effective-grant inventory for host-authenticated live tools |
| C3 production credential/mount exclusion | Offline container checks reject credential environment names, extra mounts and Docker socket | Host's live Cortex connection remains outside that offline boundary; not a proven production credential sandbox |
| C4 egress and triggers | Offline container network-none and connection-denial probes; repository workflow has no schedule or deployment step | Live Cortex probes intentionally use the host connection; repository-wide hooks/settings were not audited |
| C5 fixture routing | Exact synthetic allowlists, markers and immutable bindings; stale sources and targets held | Synthetic classification and authorized account binding depend on the operator/host |
| C6 durable state | SQLite atomicity, process termination recovery, bounded ENOSPC recovery, Cortex create/reuse/restart and one update | No power/device-loss or long-term durability proof; uncertain live update reply remains untested |
| C7 independent readback | Fresh storage/tool reads, exact identity/content/version/dependency comparisons and Cortex Flash | Independent storage observation is not independent human review; author review only |
| C8 stop, teardown and retention | Ordinary container/staging cleanup; hosted runtime reported 90-day logs within policy | Forced host-kill cleanup and future log deletion unproven; selected Git evidence persists; Cortex fixtures retained for owner review |
| C9 ownership/fencing | Single-worker contract and sequential stale-baseline guards | No atomic remote expected-version/CAS, worker lease or stale-worker fencing; concurrent workers excluded |
| Reciprocal external endpoints | No evidence of implementation | F04 remains outside implemented scope; a Cortex dependency chain is not reciprocal endpoint registration |
| Knowledge processing | Payload preservation and persistence only | Research follow-through, semantic synthesis and knowledge mastery not demonstrated by these tests |

**Full foundation acceptance remains BLOCKED.** The scoped single-worker synthetic milestone can be reviewed separately without claiming that these broader gates passed.

## Merge order and concrete follow-through

1. Review PR #2 and make a separate owner merge decision for its synthetic mission scope.
2. After PR #2 lands, retain the mission-scenarios branch until the stacked PR bases are settled. Retarget PR #4 to main (or use GitHub's resulting base only after verifying it). Re-read the diff and exact new head/base. Its scope must remain the Cortex adapter plus its own workflow/evidence changes, with no paused Notion implementation included.
3. Establish a test trigger for the intended merge destination before relying on automatic validation. The current workflow only handles pushes on foundation-audit-draft, mission-scenarios and cortex-adapter: it has no main push, pull_request or workflow_dispatch trigger. A GitHub mergeable/clean state is not proof of a required CI gate. An explicit follow-up can add main push and appropriate PR coverage, preserve empty token permissions and the isolated runner, then verify the resulting run.
4. Validate the actual PR #4 merge candidate against its final base. Reusing historical source evidence is justified only when the relevant source/workflow trees match; any runtime/workflow change needs a new hosted run. CI on the source branch currently does not test a GitHub-generated merge commit automatically.
5. Make a separate owner merge decision for PR #4's single-worker synthetic adapter scope. This review does not merge, retarget, mark ready, reactivate Nexus, deploy a callback or promote any Cortex record.
6. Keep PR #3 paused. It is a sibling of PR #4, not a prerequisite. If later resumed, reconcile its differing workflow branch list with the Cortex workflow, retarget to the then-current main and run the combined suite. Do not infer combined compatibility from the two separate branch results.

The main-trigger gap is a follow-through blocker to claiming automatic post-merge validation, not evidence of an adapter defect. Independent review remains absent from this assessment. Concurrency, reciprocal registration, power-loss and production scope must remain explicitly excluded unless separately implemented and demonstrated.

## Current review result

- PR #2 → PR #4 is the recommended order; PR #3 stays on hold.
- Current Git compatibility is clean, but no owner merge authorization or independent review is inferred.
- Existing offline and live evidence supports bounded, single-worker synthetic persistence/recovery.
- C08 subsequently implemented destination/PR CI coverage and verified the recorded source and merge-candidate runs; see the follow-through below.

## C08 CI follow-through

The workflow gap identified above was subsequently addressed on PR #2 and PR #4. Main pushes and PRs targeting main/mission-scenarios are configured, event/ref concurrency is isolated, and PR jobs verify the fetched merge candidate's current named base-branch SHA and event head SHA, retaining any historical event-base mismatch separately. PR #2 passed 32 tests and PR #4 passed 52 tests on their recorded source and actual PR merge candidates, each with four separately counted bounded faults. See [CI coverage and exact run evidence](ci-coverage.md).

Main is unchanged; its first actual push run remains to be observed after an approved merge. Required-check enforcement and independent review were not configured or established. Revalidate PR #4 after the PR #2 workflow backport and again after any later base retarget/merge. The C08 Cortex evidence issue records the final follow-up candidate result after this documentation publication. Full acceptance remains BLOCKED and PR #3 stays paused.

## C09 owner-approved PR #2 merge

PR #2 was marked ready and its ready-for-review run 39888230369 passed. The owner-approved, expected-head-pinned merge then created main commit `08464ae2a7f169bf37a569ecf9e6766da9e3d50f`. Independent PR and branch reads confirmed the merge. Actual main push run [39888300351](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39888300351) passed 32 tests and all four bounded faults, including source/boundary checks and cleanup. See [retained evidence](pr2-merge-followthrough.json).

PR #4 was retargeted to main and remains draft/unmerged. Its branch is synchronized with the actual main commit after checking that no main file is missing and only the intended README/REVIEW files differ among existing main files. Fresh merge-candidate CI must pass against this main before its separate owner merge decision. The old tables and pending-main statements above describe prior review checkpoints; they are superseded by this follow-through for PR #2 only. PR #3 remains paused. Full foundation acceptance and production/canonical activation remain excluded.

## C10/C11 follow-through

PR #4 was owner-approved and merged at `62265e0d5bf3f371b965eab7f953dc9230501eaf`. Actual main push run 39889605147 passed 52 tests, four separately counted bounded coordinator faults, boundaries/manifests and cleanup. This supersedes the earlier PR #4 merge-pending snapshot for this scoped milestone.

C11 subsequently verified recovery from one live synthetic update whose successful reply was deliberately discarded locally. A separate Python process reopened the original plan/journal, made 11 reads and no writes, verified exact v3 state and blocked a stale v2 request. Metadata and four-module/three-edge closure were independently checked. See [C11 result](cortex-c11-live-result.json) and [probe](cortex-c11-probe.py). This closes the bounded uncertain-update acknowledgment/restart observation gap; actual network interruption, abrupt-kill/power/device loss, concurrency/fencing, reciprocal registration, long-term durability and independent human review remain unproven. Full foundation acceptance remains BLOCKED; Notion integration stays paused.

## C13 focused author review and identity defect

A focused review of merged main `ce7ad5e8bf1f5b968e6cd9334b91716f90ad76ed` reproduced an identity-verification defect: after verified create ID A was replaced by B, the first retry stored B in the latest receipt, allowing the next retry to verify B. This is a blocker for the affected exact-ID claim; prior test/live results did not cover this sequence.

The proposed fix uses the earliest VERIFIED journal event as the stable create identity and the immutable before snapshot for update identity. Four new regressions failed before the fix; the full local suite passed 56 after it. This remains a proposed branch change until reviewed/merged and main CI is observed. See [finding, fix and audit limits](implementation-review.md). No live fixture was modified. Author review does not satisfy the independent-review gate. The eight-of-nine coverage count is not a completion percentage; full acceptance remains BLOCKED and Notion stays paused.


## Proposed journal identity safeguard — 2026-10-23

The proposed change in this branch supersedes the earlier no-history-detection statement for the specific inconsistencies below. It stores the first VERIFIED module ID in `cortex_identity_anchors` in the same SQLite transaction as the verification receipt and event. Before any transport call, the adapter checks that a retained receipt has events, the latest event equals that receipt, and an existing anchor matches the earliest VERIFIED event. Orphaned events/anchors also stop execution. Missing or inconsistent records raise `JournalIntegrityError`; they do not reset the journal or access Cortex. Restore an independently trusted complete journal backup before resuming; no automatic repair is supplied.

Complete trusted legacy journals backfill their earliest VERIFIED identity before transport access. This migration cannot establish whether history was already selectively lost before an anchor existed. Pending write intent without a VERIFIED event remains eligible for read-only reconciliation; IDs observed before verification remain unpinned. A failed anchor insertion rolls back the verification receipt/event atomically, preserving the earlier durable write intent for reconciliation without another write.

Seven new regressions failed the previous code (five assertion failures and two missing-table errors). The modified local suite passes 63 tests. Cases cover complete history loss with a replacement or original module, trusted restore, latest-event loss, first-verification loss with a later foreign identity, legacy migration, anchor transaction failure and orphaned records. Hosted candidate evidence is reported separately in the PR.

This is detection of specific inconsistent retained records, not authenticated history or complete truncation detection. Total database loss/replacement, coherent rewriting of all related records, and incomplete history predating migration remain outside the guarantee. Retain complete history and trusted backups. The independent AI report reviewed the earlier frozen revision, not this implementation; fresh review and human review remain open. Single-worker scope remains mandatory; no remote CAS or fencing is added. Full acceptance remains BLOCKED; Notion stays paused.
