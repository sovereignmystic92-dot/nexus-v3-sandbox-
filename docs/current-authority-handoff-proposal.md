# Current-authority handoff — review proposal

Status: DRAFT SECURITY-CONTROL PROPOSAL. Not an adopted authority rule or executable permission.
Scope: existing single-worker sandbox, saved checkpoint observation to a gated executor.
No workflow, credential, permission, scheduler or runtime changes are installed.

## Verified starting point

[Read-only run 40871262428](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/40871262428), attempt 1/job 123438613721, ran main
515141f30ca57ad79800a6be386f4889e639484f. It matched checkpoint
NXS-LIVE-CHECKPOINT-40862662915 with digest
7409a0f2aae701d8d1c4cbce51426d96f455ec989f8e966ea3243696bdca17a8,
using eleven reads, zero writes and zero executor callbacks.
Observed next stage SOURCE_PRESERVED; no completed receipts or pending mutation.
The classifier deliberately returned BLOCKED/VERIFY_CURRENT_AUTHORITY.
A successful read does not attest identity, effective grants, authority or fencing.

## Reuse before adding machinery

[PR57](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/pull/57)
head dc9b5ef508cb8557ea512ba4c0584c8dc66dd4c9 already proposes
approval receipts and ApprovedWriteBoundary with intent/baseline/payload binding.
It is not adopted. Its configured trusted-reviewer set is empty; its body records
a historical trusted-base bootstrap failure. Receipt model/independence fields
are attestations, not provider authentication. Do not create a competing guard.
The adopted checkpoint transport, codec, resume classifier and pipeline remain
the state contracts. The synthetic authority resolver explicitly accepts
operator-supplied assertions and cannot authenticate real authority.

## Proposed evidence required by the trusted host

The following is a review checklist, not a new acceptance criterion or an
implemented schema. Applicable current Nexus rules and native controls prevail.

| Binding | Required observation | Hold condition |
| --- | --- | --- |
| Mission and operation | Current owner-authorized bounded purpose, exact next stage and permitted operation | Missing, ambiguous, reserved or out-of-scope action |
| Code and governance | Exact executor revision, current governing source revisions and applicable adopted decisions | Revision drift or conflicting current decisions |
| Execution identity | Provider/connector-authenticated actor, credential reference only, attributable execution/run/attempt | Self-reported actor, unknown linkage or changed identity |
| Destination and request | Enrolled destination, source/checkpoint identities and hashes; immutable request/payload and baseline | Wrong destination, changed request or unexplained baseline |
| Current access | Attributable applicable capabilities, scope restrictions and native approval result | Denied operation or unknown operation-dependent enforcement |
| Observation completeness | Independently fetched exact checkpoint chain and complete bounded inventory | Missing, truncated, duplicate, tampered or stale state |
| Single-worker boundary | Existing restriction preserved and applicable serialization controls observed | Concurrent or ambiguous execution; do not claim remote fencing |
| Consequential-write transition | Recheck affected bindings, then save exact durable intent before any effect | Changed authority/context or uncertain preceding outcome |

A full CP02–CP04 inventory remains separate from bounded operation permission.
Accepted exceptions do not justify inventing missing operation-dependent evidence.
Do not request secret values or infer a complete grant inventory from a successful call.
Timestamp recency alone does not authenticate a receipt. The host must obtain evidence
from trusted observations rather than checkpoint contents or candidate JSON.
An unsigned JSON packet, CLI flag, callback PASS or model statement alone cannot
set authority_verified=True.

## Proposed handoff order

1. Read current authoritative rules and scoped mission; check existing work.
2. Observe the saved checkpoint through the adopted read-only transport.
3. Collect operation-dependent authority evidence through an approved host adapter.
   No such authenticated collector is supplied by this proposal.
4. Resolve every required binding against current context. Missing evidence stays
   UNKNOWN/BLOCKED; an actual denial remains distinct from unavailable evidence.
5. Only after approved implementation and review may the trusted host pass a
   verified authority decision to the classifier. Do not expose a user-editable
   boolean as the authority mechanism.
6. A classifier READY result is a plan, not dispatch permission. The existing
   pipeline must recheck prerequisites and durably save intent before a mutation.
7. An uncertain result permits observation/reconciliation only, never blind replay.
   Recheck material identity/code/grant/destination/control changes.
8. Save attributable outcome and independent readback before claiming completion.

The live observer remains hardcoded authority_verified=False. This proposal must
not change it, connect an executor or grant a new provider operation.

## Validation required before integration

Use existing contracts and synthetic fixtures to demonstrate rejection of changed
actor/credential reference, destination, source/checkpoint hash, code/governance
revision, operation/request/baseline, revoked approval, incomplete inventory and
unsupported concurrency. Test missing, malformed and self-issued evidence as holds.
Demonstrate context changes between classification and dispatch prevent the effect.
Demonstrate fresh-process uncertain-outcome recovery observes without repeat mutation.
Keep synthetic authentication substitutes explicitly labeled; passing those tests
cannot validate real provider authentication or remote enforcement.

## Concrete blocker and next bounded step

Select and review an authenticated evidence source available to the trusted host.
Current read-only workflow receives a Notion credential reference and GitHub context,
but no authenticated operation-authority collector is wired. PR57's empty reviewer
trust configuration cannot supply that missing evidence, and populating it or
altering controls is outside routine maintenance authority. Review PR57's existing
contracts against this checklist before scoped adapter implementation; separately
authorize any identity provisioning, permissions or security-control activation.
No new live probe is proposed here. Owner conversational approval alone does not
supply authenticated runtime identity evidence.

CP09 remains paused and NOT_PROVEN; do not implement worker fencing under this task.
Production and broad bridge remain inactive. No tracker or acceptance score changes.
Rollback of this documentation-only proposal is a normal reviewed revert.
