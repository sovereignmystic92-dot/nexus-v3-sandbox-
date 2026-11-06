# CP05 synthetic destination-binding acceptance candidate

Status: PROPOSED / NOT EXECUTED. This document is a test specification, not proof of CP05 closure.
Scope: Nexus synthetic sandbox only. No production credentials, provider writes, new grants, or automatic activation.

## Existing checkpoint definition
Every operation must bind immutable synthetic IDs, verified account/root markers, and allowlisted destinations. A wrong account or destination must be denied before mutation.
Required evidence: positive and negative fixture-routing tests plus independently fetched identity/destination evidence.
Keep CP05 PARTIALLY_VERIFIED until every original requirement is demonstrated; do not redefine the gate merely to improve the 19-checkpoint score.

## Test matrix
1. Positive: verified synthetic caller, immutable fixture ID, approved root/account and allowlisted destination. Assert exactly one bounded mutation; fresh independent reader confirms identity, destination, content hash, version and dependencies.
2. Wrong account: same fixture ID with mismatched authenticated account. Assert fail closed *before* provider mutation, zero writes, and unchanged independently read destination.
3. Wrong root/destination: valid caller with unallowlisted root or wrong output store (Notion transcript archive versus Cortex analytical output). Assert zero writes and unchanged destination.
4. Missing/ambiguous identity or grants: absent identity, stale marker, or unverifiable effective permissions. Assert fail closed and no write.
5. Enrollment/creation: unapproved fixture or destination cannot be created/enrolled. Approved synthetic creation is bound to the same immutable IDs and allowlist.
6. Guarded update: approved synthetic update is version-bound; stale revision, duplicate request, and conflicting target are denied or reconciled without duplicate mutation.
7. Recovery: crash after uncertain acknowledgment and restart. Reconcile against independent provider state before retry; never blindly replay an uncertain write.
8. Host routing: demonstrate that all relevant execution surfaces, including connector-mediated paths, are covered by enforcement or explicitly mark out-of-guard paths as blockers.

## Required evidence per case
- Exact source revision, test invocation, runner identity and effective grant inventory (no credential values)
- Immutable fixture/account/root/destination identifiers or safely hashed identifiers
- Preflight decision and observed provider request/write counts
- Fresh independent readback of both intended and denied destinations
- Fault injection trace and restart/reconciliation evidence where applicable
- Negative cases must prove *no mutation*, not just an exception string
- Independent reviewer disposition with unresolved scope exclusions

## Acceptance rule
No CP05 promotion without attributable hosted tests, verified identity/grants, guarded live synthetic update and creation/enrollment where required, full host routing coverage, and independent evidence review. A successful mock is not proof of live provider behavior. CP09 remote fencing remains separate and open. No merge or activation without current-base CI and required review.

## Execution status
Not run. No evidence of a passing new test. Next: implement isolated tests against the existing guard and submit for review.
