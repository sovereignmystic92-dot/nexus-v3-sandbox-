# Foundation audit status — 2026-10-23

**Full foundation acceptance: BLOCKED.** This is an author-maintained evidence handoff, not independent human signoff. It supersedes earlier status and merge-pending summaries for the revision below; historical evidence remains attributed to its original revision.

## Verified baseline

Main revision: `4b396f64b1b1174a9f3da0366a82a530453067e9`. [PR #8](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/pull/8) is merged. [Actual main run 39910994470](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39910994470) passed **63 distinct tests**, including four mission cases, plus **four separately counted coordinator fault checks** (three SIGKILL boundaries and bounded tmpfs ENOSPC). Boundary probes and ordinary container/source-staging cleanup passed. These faults do not test live Cortex outages or power/device loss.

The adapter retains immutable request bindings, durable write intent and independent source/target readback. Uncertain writes reconcile without a blind repeat. Creates retain their first durable VERIFIED identity; updates bind the exact before-ID. PR #8 adds an atomic identity anchor and stops before transport access on specific missing/inconsistent retained-record conditions. Complete trusted legacy history can backfill the anchor; this does not certify that legacy history was complete. [Contract and limits](cortex-adapter.md).

Earlier live observations demonstrated synthetic create/reuse/restart (C05), update and stale-target preservation (C06), and recovery across a normal restart after a successful update reply was deliberately discarded locally (C11). Those are observations of earlier revisions, not live retests of PR #8. Old probes use historical baselines and must not be blindly replayed.

Notion remains authoritative. [PR #3](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/pull/3) is open, draft and paused at `db84ec6961528c5b1a080e0c42b5ef56f0781c9e`. No production deployment, canonical promotion or unattended live callback is established.

## Control disposition

| Control | Evidence available | Remaining gate |
| --- | --- | --- |
| C1 isolation | Hosted read-only source, nonroot container, bounded resources and boundary probes | Shared kernel/provider trust; broader host boundary not independently audited |
| C2 identity and grants | Offline UID/configuration checks; historical live owner metadata | Complete effective grants for host-authenticated live tools not independently audited |
| C3 credential/mount exclusion | Offline credential-name, mount and socket restrictions | Live host connection remains outside the offline container boundary |
| C4 egress and triggers | Network-none and denial probes; configured main/PR CI | Live host egress and complete repository settings/hooks inventory not established |
| C5 fixture routing | Exact synthetic allowlists/markers and immutable bindings | Account selection and truthful fixture classification remain host/operator assumptions |
| C6 durability | Atomic transactions, bounded coordinator kill/ENOSPC recovery, historical live restart recovery, identity-history checks | Total database loss/replacement, coherent rewriting, pre-migration history loss, power/device loss and long-term durability |
| C7 independent readback | Fresh exact storage/tool comparisons; historical Flash | Storage readback is not independent human review; latest safeguard has separate AI review; human review remains open |
| C8 teardown/retention | Ordinary cleanup passed; runner reported 90-day logs | Forced host-stop cleanup and future deletion unproven; committed evidence persists |
| C9 ownership/fencing | Documented single-worker restriction and sequential conflict checks | No enforced remote CAS, worker lease or stale-worker fencing; multiworker execution excluded |

Eight controls have some bounded implementation or evidence; that is **not an audit completion percentage**. None of this table grants unrestricted production acceptance. Reciprocal external endpoint registration and semantic research/knowledge-mastery acceptance remain outside the implemented persistence milestone.

## Review provenance

The [independent AI report](independent-review/independent-review-report.md) covers frozen revision `618681fdc6d1767358cca993e857f68fd2202879`, reproduced 56 tests and identified the history-loss boundary later addressed in part by PR #8. It is not a review of the new identity-anchor implementation and is not human audit. A subsequent [independent AI review of PR #8](independent-review-pr8/independent-review-report.md) reviewed frozen implementation `4b396f64b1b1174a9f3da0366a82a530453067e9`, independently reproduced 63 tests and seven targeted regressions, and added twelve probes. Its recommendation accepts only the documented retained-record identity safeguard under trusted-journal/single-worker assumptions. Three probes demonstrate limitations, so their passing assertions are not safety claims. Prior-adapter contrast reproduced five assertion failures and two missing-table errors. Raw evidence, reproduction scripts and reviewer hashes are retained alongside that report.

PR #8 has author review and six additional offline probes recorded in its description; these are separate from the 63 hosted tests. They do not increase the hosted test count. The subsequent separate AI review is distinct from those author probes and does not satisfy human review. No submitted GitHub review was returned during the focused PR #8 review.

A reviewer of the current baseline should inspect `src/nexus_sandbox/cortex_adapter.py`, `cortex_tools.py`, `tests/unit/test_cortex_adapter.py`, the workflow and runner, the PR #8 diff, and its exact candidate/main run provenance. Reproduce with `python3 tools/validate.py --output review-validation.json`; this command alone does not run the isolated faults or call live services. Record reviewed SHA, commands, observed outcomes, findings, exclusions and reviewer identity. Pay particular attention to transaction rollback, legacy migration trust, pre-VERIFIED identity changes, missing-record stops and recovery without duplicate writes.

## Next technical decision: C9

Keep execution single-worker until an enforceable remote ownership design is available. A local journal lock would only coordinate cooperating processes sharing that lock; it would not fence another host, independent journal, direct tool caller or an expired worker's remote write.

Before implementing multiworker support, define the remote mutation boundary and require conditional writes tied to a monotonic ownership token, or a single write gateway with enforceable exclusive authority. The currently exposed Cortex update tool has no expected-version/CAS parameter. Sequential preflight/readback cannot substitute for an atomic remote condition.

Acceptance cases for a future design must include simultaneous acquisition (one winner), expiration and takeover, delayed stale-worker write after takeover (rejected at the actual mutation boundary), gateway/service restart with preserved ownership, and uncertain write reconciliation without duplicate mutation. Offline model results alone cannot establish those remote guarantees. Until the required backend capability and authority boundary are demonstrated, C9 remains open; no concurrency claim or deployment follows from this plan.


## Open low-severity review finding

The PR #8 reviewer found that the dictionary/schema walk stops at the earliest VERIFIED event. A syntactically valid nonobject event later in history can escape that check when a final event still matches the latest receipt. The original identity remains pinned and no extra write occurred in the reproduction; this is nonblocking for the declared narrow guarantee. Do not claim every retained event is schema-validated. A focused follow-up can validate all decoded event types before selecting the earliest verification, with a regression for a nonobject tail. This publication does not change runtime behavior. Human review and full foundation acceptance remain open.


## Proposed malformed-event follow-up

The follow-up branch moves the object-type check ahead of earliest-VERIFIED selection, covering every decoded event for the requested key, including intermediate and latest tail entries. Nonobject JSON events raise `JournalIntegrityError` before any transport call. Syntax-invalid JSON still stops during decoding. The first VERIFIED ID selection and legacy migration rules are unchanged. Object-type checking is not full receipt-schema validation, authentication or proof of complete history.

Two new regression methods cover six nonobject JSON types with a matching final receipt, plus a matching nonobject latest receipt/event. They assert zero new reads or writes and exact journal preservation on the hold; the first also checks recovery after restoring the trusted prior records. The prior adapter produced seven assertion failures across these two methods. The proposed adapter passes both and the 65-test local suite. See [raw before/after evidence and commands](malformed-history-regression-evidence.json). This is an author-tested proposed fix, not a change to the attributed independent report or a fresh independent review. The finding remains open on main until the follow-up is merged and verified. Human review, C9 and full acceptance remain open; Notion stays paused.
