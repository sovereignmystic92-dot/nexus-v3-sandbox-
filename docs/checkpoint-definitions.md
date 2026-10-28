# Nexus checkpoint definition and update procedure

Definition version: proposal-1 (identifier retained for evidence continuity). Owner accepted this 19-item definition set on 2026-10-24 after reviewing PR #23. This is a newly adopted mapping, not a recovered original checklist. The historical report of 8/19 remains an UNRECONCILED aggregate; no checkpoint is retroactively marked passed. The accepted count under this proposal is NOT ESTABLISHED, rather than zero or nine. Existing evidence is preserved.

The machine-readable record is [checkpoint-register.json](checkpoint-register.json). Source basis: `docs/foundation-audit-status.md`, `docs/test-plan.md`, `docs/current-acceptance-review.md`, and `docs/audit-network-recovery-readback-cleanup.md` at main `709a4d39d1c0058d3f4dc8c8832025ad324d55b5`. C1-C9 control labels and test-case C01/C02 are different namespaces. The grouping below explicitly combines related scenarios and adds independent human review; owner acceptance of this mapping is recorded; reconciliation of the historical eight and individual PASS adjudication remain open.

## Meaning of a checkpoint

A checkpoint is a versioned acceptance requirement for an explicitly declared operating scope. A successful test supplies evidence; it does not automatically establish the entire requirement. All conjunctive conditions and scope requirements must be met before PASSED. An unavailable prerequisite is BLOCKED; observed nonconformance is FAILED; incomplete positive evidence is PARTIALLY_VERIFIED.

## Adopted fixed inventory

| ID | Checkpoint | Source mapping |
| --- | --- | --- |
| CP01 | Host and filesystem isolation | C1 |
| CP02 | Identity and effective grants | C2 |
| CP03 | Credential and mount exclusion | C3 |
| CP04 | Network and triggers | C4 |
| CP05 | Synthetic fixture and destination binding | C5 |
| CP06 | Durability and recovery | C6 |
| CP07 | Independent readback | C7 |
| CP08 | Stop, cleanup and retention | C8 |
| CP09 | Remote ownership and fencing | C9 |
| CP10 | Independent human review | review |
| CP11 | Complete transaction and exact repeat | S01/S02 |
| CP12 | Idempotency binding conflict | S03 |
| CP13 | Incomplete source hold | S04 |
| CP14 | Forbidden destination hold | S05 |
| CP15 | Authority precedence and source instructions | S06/S07 |
| CP16 | Recovery after source archive | F01 |
| CP17 | Recovery after output before registration | F02 |
| CP18 | Reciprocal connection registration | F04 |
| CP19 | Readback and storage failure safety | F03/F05 |

Each JSON entry specifies the actual pass requirement and necessary evidence. NOT_TESTED means not assessed under this proposed definition; it is not a claim that historical tests never ran. Dependencies must be populated during scope assessment; an empty list currently means unspecified, not proven independent.

## Update after a successful test

1. Bind the observation to checkpoint ID, definition version, exact source commit SHA and tested operating scope.
2. Retain the test command/case IDs, run URL, tested revision, execution time, operator/reader identity, expected result, actual result, artifact identities/hashes, operation outcome, protocol verdict and limitations. Never record credentials or production payloads in this public repository.
3. Re-fetch the committed evidence or destination through a fresh reader and record the comparison. For an offline test this validates its evidence artifacts; it does not become proof of an external write.
4. Assess the whole pass requirement. Record covered conditions, unresolved blockers and explicit dependencies. All required evidence and dependencies must be satisfied before PASSED. A single passing case may only justify PARTIALLY_VERIFIED.
5. Append a history entry with previous/new status, evidence reference, reason and attributable assessor. Set assessed_revision, scope and evidence. For PASSED also set accepted_by and accepted_at. Human review is mandatory where the checkpoint specifically requires it; the author cannot substitute their own signoff for CP10.
6. Publish the bounded update through a reviewable PR. Preserve old observations; never overwrite failed results with a later pass. Merging documentation alone does not close a gate.
7. Derive the score from eligible PASSED entries only after the definition set is accepted and legacy reconciliation is recorded. A change to requirements or denominator requires a new definition version and explicit disposition, never silent renumbering.

## Evidence record shape

Use one object per observation in `evidence`:

```json
{
  "evidence_id": "unique-observation-id",
  "definition_version": "proposal-1",
  "source_sha": "exact-tested-commit",
  "scope": "explicit-host-adapter-and-fixture-boundary",
  "case_ids": ["actual-test-id"],
  "command": "actual-command",
  "run_url": "provider-issued-run-url",
  "observed_at": "ISO-8601-UTC",
  "operator": "attributable-operator",
  "expected": "required-observation",
  "actual": "observed-result",
  "operation_outcome": "SUCCEEDED",
  "protocol_verdict": "PARTIALLY_VERIFIED",
  "readback": {
    "reader": "attributable-fresh-reader",
    "artifact_reference": "exact-evidence-or-destination-reference",
    "comparison": "MATCHED"
  },
  "limitations": ["remaining-scope-limit"]
}
```

This shape is documentation, not an installed JSON Schema validator or automatic updater. No background job, secret access, live API call, production mutation or automatic promotion is added.

## Reopening and acceptance boundaries

A failed relevant retest or loss of evidence reopens an accepted checkpoint. A source/configuration change requires impact assessment: retain its historical pass at the old SHA, but mark current applicability unassessed or REOPENED until justified by evidence. Missing or mismatched identity/currentness fails closed. A positive operation outcome can coexist with an incomplete protocol verdict.

Single-worker deferral of remote fencing does not pass CP09. Shared-filesystem process recovery does not prove total-host-loss recovery. Container network denial does not establish host-wide egress controls. A held deployment does not prove successful approval release or server-side branch denial. Owner approval of a PR does not establish independent human review.

## Initial disposition

All 19 proposed checkpoints have now received an author evidence assessment against actual main run 40135860508 at `709a4d39d1c0058d3f4dc8c8832025ad324d55b5`. Retrieved logs contain 162 passing distinct tests and four separately counted fault checks. The report is retained in [checkpoint-evidence-main-709a4d3.json](checkpoint-evidence-main-709a4d3.json); tests were not rerun during this mapping.

Eight proposed requirements have supporting bounded SQLite evidence: CP11, CP12, CP13, CP14, CP15, CP16, CP17 and CP19. These are candidate assessments, not a reconstruction of the historical eight. Definition adoption is recorded, but they remain PARTIALLY_VERIFIED until individual PASS adjudication records that all conditions for the declared scope are met. No accepted score is derived yet.

CP01/03/04/05/06/07/08 have partial evidence and material scope gaps. CP02/09/10/18 are BLOCKED. In particular, CP04 cannot close from workflow-byte checks and container probes alone; its missing host/settings/hooks and server-side gate evidence is substantive. CP18 lacks reciprocal endpoint implementation and is not a documentation-only closure.

The previously quoted 8/19 is retained with its mapping gap. No ninth gate is claimed and no gate is weakened to meet a numerical target. A decision to adopt this proposal must be recorded as a new baseline with a transparent legacy reconciliation, rather than asserting that matching candidate counts prove historical identities.


## Owner adoption — 2026-10-24

The owner replied “Approve” after presentation of the PR #23 register and its adoption decision. This accepts the checkpoint definitions/register and authorizes merging this documentation change after checks pass. It does not independently certify the evidence, retroactively identify the historical eight, satisfy CP10, close a ninth checkpoint, or authorize production activation. This supersedes proposal/adoption-pending wording above for the definition set only. Individual evidence and status history remain unchanged.


## Latest individual adjudication — 2026-10-24

The [requirement-level adjudication](checkpoint-adjudication.md) supersedes the earlier assessment-pending disposition for CP11–CP17 and CP19. These eight pass within their previously declared single-worker synthetic SQLite scope; seven remain PARTIALLY_VERIFIED and four BLOCKED. The historical aggregate is preserved but superseded for scoring without asserting historical identity matches. This creates a traceable new 8/19 baseline when merged; no ninth gate or production readiness follows. Earlier history/evidence entries retain their original dated wording.


## Owner-authorized CP08 sandbox closure — 2026-10-28

Definition version: owner-cp08-sandbox-2026-10-28. The owner directed leaving CP09 unchanged and closing CP08 if its sandbox tests pass. This prospectively replaces CP08's acceptance scope with single-worker synthetic hosted-sandbox cleanup on a surviving Docker host, including ordinary cleanup, catchable runner stop and abrupt runner loss with an explicit surviving foreground supervisor. Owned container and staging absence must be independently observed; retained evidence must have an explicit bounded retention setting.

Fresh run [40638902063](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/40638902063), job 122652171244, tested merge candidate ca06264ddd79717f704051b5b9afee7bd01fac1e integrating PR #42 onto current main. All 277 distinct tests, four faults, real-Docker SIGTERM and SIGKILL/surviving-supervisor cases passed. Both owned container and staging removal were observed; runtime log retention was 90 days. See [bounded evidence](cp08-sandbox-closure-20261028.json).

CP08 is PASSED under this sandbox-only definition. The original broader requirement is retained as PARTIALLY_VERIFIED in register history: total-host-loss cleanup, future retention expiry and provider/backend erasure remain unverified. No automatic recovery supervisor was installed. This is an explicit scope amendment, not proof of those excluded guarantees. CP09 and every other checkpoint disposition remain unchanged. Revised score: 12/19 (four partial, three blocked), definition-dependent. No production readiness or new operational activation follows.
