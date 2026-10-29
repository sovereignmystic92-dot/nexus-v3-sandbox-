# Inactive approval verifier bootstrap

Implements Stage A of PR83 only. Source PR57 revision: 76eeb264281e50b9d85ed31ccc7bff2cbb8a0db3.
Base main: 515141f30ca57ad79800a6be386f4889e639484f.

The initial verifier and policy were copied from that source. Independent review
identified latent defects; the verifier is now hardened as recorded below. Policy
remains unchanged and empty-trust. The context test uses a schema-valid fixture. The guard unit tests omit only the workflow-preflight ordering test:
this inactive package deliberately installs no workflow changes, so that assertion
belongs to PR57 activation validation. Three bootstrap regressions verify empty
trust and missing policy hold before network calls, and production remains denied.

This package adds no workflow, scheduler, write boundary, identity enrollment,
credentials, permissions, protected check or runtime invocation. The existing
synthetic suite may discover the unit tests; all provider observations are mocked.
An installed file is not an enforced approval control.

## Provenance blobs at source
- tools/approval_gate.py: a63c90e79638c4d3645b99771ec6464ba13d6e1b
- tools/approval_policy.json: 14d44288c4afacb0488a694542878f6dce9ffa9f
- tests/unit/test_approval_gate.py: 7b0986322d2bb196f866a9c346ba9494dfad6a7f
- tests/unit/test_approval_context_recheck.py: 3242ec9713379b5a18cadc0468be6dccf36e43b4

## Validation and limits
23 focused offline tests passed locally: 11 guard, 4 context drift, 3 inactive
bootstrap, 5 security hardening regressions. This is primary-author validation, not independent review or hosted
current-base validation. Policy containers/types, session whitespace, evidence path traversal and nonstandard
JSON constants are hardened. API proxy behavior, further adversarial receipt parsing,
trusted base provenance and actual reviewer enrollment still need activation review.
Synthetic account names in tests are not enrolled identities.
Model/session/independence remain reviewer attestations, not provider signatures.
No provider-side atomic approval/dispatch or worker fencing is supplied.

## Adoption sequence
1. Inspect complete diff, focused cases, actual hosted logs and exact head/base.
2. Obtain independent security-control review and specific adoption authorization.
3. Preserve all native gates; no temporary exception, candidate-code fallback,
   self-certification, fabricated receipt or policy weakening.
4. Before an authorized merge save and independently fetch exact revision/evidence,
   scope and rollback checkpoint. Merge normally with head binding when supported.
5. Independently fetch main files and observe main checks. Only then is missing-file
   installation resolved; empty trust must still HOLD.
6. Reconcile PR57 against installed main and renew affected reviews. Actual distinct
   reviewer identities and separately reviewed activation remain prerequisites.

Rollback: normal reviewed revert of the exact bootstrap merge, preserving evidence.
No score promotion, live-provider probe, CP09 resumption or production activation.

## Independent review findings and draft repairs
Reviewers A/B independently approved initial inactive scope only, then separately
reproduced latent activation weaknesses. Stable findings:
- AUTH84-POLICY-TYPE: destination string substring match and malformed trust reaching
  observation. Strict policy schema/container/identity validation now precedes network
  and authorization; malformed policy holds.
- AUTH84-SESSION-SPACE: whitespace variants could count as distinct sessions.
  Identity/session strings with surrounding whitespace are rejected.
- AUTH84-EVIDENCE-PATH: prefix-only blob paths allowed traversal or ambiguous URLs.
  Evidence permits exact run URLs or conservative nonempty file segments under the
  exact revision; dot segments, encoded paths, queries and fragments hold.
- AUTH84-JSON-CONSTANT: NaN/Infinity accepted by default JSON parser. Explicit
  parse_constant rejection now holds.

New regression cases failed against the initial verifier, then passed after repair.
The initial malformed-trust test mocked public_get but overlooked review_list's
definition-bound default callback; it attempted unauthenticated public API reads
before that harness path was corrected. No credentials or mutation were involved;
response/access outcome was not retained, so no provider assurance is inferred.
Final harness mocks review_list as well. The context CLI regression asserts the
authorization callback was reached before the final drift hold, avoiding a false
positive caused by an invalid policy fixture.

Initial review approvals do not approve these changed files. Renew independent
review and exact current-base hosted validation before readiness/adoption. No
activation or trust-policy changes are included.
