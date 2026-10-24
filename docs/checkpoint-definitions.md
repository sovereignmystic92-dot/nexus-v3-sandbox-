# Nexus checkpoint definition and update procedure

Definition version: proposal-1. This is a new proposed 19-item mapping, not a recovered original checklist. The historical report of 8/19 remains an UNRECONCILED aggregate; no checkpoint is retroactively marked passed. The accepted count under this proposal is NOT ESTABLISHED, rather than zero or nine. Existing evidence is preserved.

The machine-readable record is [checkpoint-register.json](checkpoint-register.json). Source basis: `docs/foundation-audit-status.md`, `docs/test-plan.md`, `docs/current-acceptance-review.md`, and `docs/audit-network-recovery-readback-cleanup.md` at main `709a4d39d1c0058d3f4dc8c8832025ad324d55b5`. C1-C9 control labels and test-case C01/C02 are different namespaces. The grouping below explicitly combines related scenarios and adds independent human review; owner acceptance of this mapping and reconciliation of the historical eight are still needed before adopting it as the fixed denominator.

## Meaning of a checkpoint

A checkpoint is a versioned acceptance requirement for an explicitly declared operating scope. A successful test supplies evidence; it does not automatically establish the entire requirement. All conjunctive conditions and scope requirements must be met before PASSED. An unavailable prerequisite is BLOCKED; observed nonconformance is FAILED; incomplete positive evidence is PARTIALLY_VERIFIED.

## Proposed fixed inventory

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

Definitions and update format created; checkpoint statuses not assessed. The previously quoted 8/19 is retained with its mapping gap. No ninth gate is claimed and no gate is weakened to meet a numerical target.
