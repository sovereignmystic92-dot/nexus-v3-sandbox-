# Focused implementation review — C13

Reviewed main: `ce7ad5e8bf1f5b968e6cd9334b91716f90ad76ed`. This is author review, not independent human review, an exhaustive security audit or full foundation acceptance. No live Cortex module was changed during this review; only the synthetic registry's context was read.

## Blocking finding: verified identity can drift on repeated reconciliation

The Cortex adapter used the latest receipt's module_id as the identity to require on the next attempt. A conflicting observation overwrote that field. After a verified create at ID A, replacing the remote module with ID B under the same name/content/dependencies/version produced:

1. Initial create: VERIFIED, ID A.
2. First read of replacement: UNKNOWN, ID B saved in the latest receipt.
3. Second read of replacement: VERIFIED, ID B.

No second remote write occurred. The defect is a false verification claim and loss of the originally verified identity, not duplicate creation. It undermines exact-ID assurance under the declared mismatch/retry contract. This was reproduced against the reviewed code with an offline transport; no live delete or replacement was attempted.

Two related cases also failed: an unverified preflight conflict could pin a foreign ID and cause a later valid create/update to report FAILED. A legacy journal containing a later incorrect VERIFIED receipt could preserve the identity drift.

Disposition: **blocking for the affected identity-verification claim until the proposed fix is reviewed, merged and its main CI result observed**. Prior 52-test passes and C05/C06/C11 live observations remain historical results for their cases; they did not exercise repeated replacement identity.

## Proposed fix

For creates, derive the stable identity from the earliest VERIFIED event for the immutable request key, rather than from the latest observation receipt. Repeated conflict observations cannot change that identity. For updates, use the target ID already bound in the exact before snapshot.

Existing event history supplies the original identity without a schema migration, including a journal whose latest receipt was incorrectly replaced by the old bug. Conflicting state remains preserved and cannot verify; restoring the original module allows read-only recovery. An unverified preflight conflict does not establish the request's verified identity.

Keep the complete journal and its event history. An unreadable/malformed verified event fails before transport access. This change does not authenticate event history, survive deletion/tampering of the journal, establish pre-verification create identity after an unacknowledged write, or provide CAS/concurrency protection. A create that has never verified is still reconciled by the documented exact name/content/version/dependencies contract.

## Regression evidence

Four new offline cases failed against the old implementation and passed after the change:

- Repeated replacement observations across journal reopenings never verify ID B, preserve remote state and perform no extra writes; restoring A verifies again.
- Earliest verified identity survives a legacy incorrect latest receipt/event at ID B.
- A removed unverified preflight conflict does not poison a later legitimate create.
- An exact update baseline remains authoritative after a temporary foreign-ID conflict.

The full local suite passed **56 distinct tests** (the prior 52 plus these four), with full_acceptance_status=BLOCKED. Hosted merge-candidate verification is recorded separately in the PR and scoped C13 Cortex evidence issue. The patched adapter has not been exercised against live Cortex.

## Audit interpretation

The focused inspection covered Cortex binding/reconciliation/readback, its tool-response mapping, synthetic authority resolution, and coordinator checkpoint/evidence transaction structure. It is not a line-by-line review of every runner or an independent permission audit.

The earlier eight-of-nine statement counts control areas with some work/evidence. It is not a completion rate. This defect demonstrates why no coverage count closes the acceptance gates.

| Control | Current evidence/limit |
| --- | --- |
| C1 isolation | Hosted offline boundary evidence; shared-kernel/provider trust remains |
| C2 identity/grants | Nonroot runner and observed Cortex metadata; complete live grants audit absent |
| C3 credential/mount exclusion | Offline checks; host live connection is outside that boundary |
| C4 network/triggers | Offline network-none verified; live calls deliberately use host connectivity |
| C5 fixture routing | Exact synthetic guards tested; classification/account binding is operator-supplied |
| C6 durability | Scoped SQLite/process/ENOSPC and live restart evidence; no long-term/power-loss proof |
| C7 readback | Exact reads and separate outcomes tested; original-ID retry defect found, fix pending merge; independent review absent |
| C8 cleanup/retention | Ordinary cleanup and 90-day runtime setting observed; host-kill/future deletion unproven |
| C9 fencing | No multiworker leases, atomic remote CAS or stale-worker fencing |

Full foundation acceptance remains BLOCKED. Notion stays authoritative and paused; production activation, canonical promotion and concurrent workers remain outside scope. The immediate next gate is review/merge of this concrete fix and verification of its actual main run, followed by independent review rather than a blanket readiness declaration.
