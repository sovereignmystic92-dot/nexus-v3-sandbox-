# Nexus Knowledge Mastery v0.1 — bounded learning contract

Status: proposed, non-operational. Reconciliation anchor: Cortex issue `issue_01m6ze53gsv1rk8jpvshfcv9nq`. This specification does not supersede the Nexus constitution or knowledge promotion contract.

## Ownership and scope
- Notion preserves source transcripts, original evidence, and revision history.
- Cortex owns derived knowledge, relationships, confidence, unresolved contradictions, and mastery evaluations.
- GitHub Actions validates contracts and records evidence. ChatGPT coordinates; Gemini can provide an independently recorded review where authorized.
- Knowledge Mastery is a capability of the existing Knowledge Layer, not a new autonomous authority.

## Learning cycle
1. **Acquire**: accept a source only with stable identity, source location, provenance and integrity/readback status.
2. **Interpret**: extract claims, concepts, and evidence references, explicitly separating observation from inference.
3. **Connect**: propose relationships to existing Cortex knowledge without silently overwriting prior conclusions.
4. **Challenge**: identify contradictions, missing evidence, source dependence, and alternate explanations.
5. **Apply**: answer held-out questions or solve a new scenario using cited evidence; record expected outcome before scoring.
6. **Evaluate**: compare against an independent rubric or reference outcome, record failure modes, and revise candidate confidence.
7. **Persist**: submit derived records to Cortex only through existing authorized promotion/write gates; preserve original sources and previous versions.

## Required evaluation receipt (logical contract)
Each attempted evaluation must record: evaluation_id, subject_id, source_refs, source_integrity_status, revision, question_or_task, rubric_version, expected_or_reference, observed_answer, score, evidence_refs, uncertainty, contradiction_refs, evaluator_identity, review_independence_status, timestamp, and outcome (pass/fail/inconclusive). Missing fields fail closed. Repeat observations from the same underlying source must not count as independent evidence.

## Mastery levels (not automatic promotions)
- L0 unassessed
- L1 source capture and accurate recall
- L2 explanation with evidence and uncertainty
- L3 cross-source connection with source independence checks
- L4 contradiction analysis and alternative hypotheses
- L5 held-out application meeting an explicit rubric
- L6 repeatable transfer across novel scenarios with documented correction of earlier failures

A level is demonstrated only by receipts satisfying a versioned rubric and provenance checks. Volume of ingested documents or model confidence alone cannot raise a level. Failed or inconclusive evaluations do not silently pass.

## Safety and constitutional boundary
Learning may propose new knowledge, tests, and changes; it cannot change constitutional authority, grants, credentials, destinations, or execution permissions. Existing approvals, independent review, idempotency, audit, retention, and provider-write gates remain binding. Historical conflicting records remain traceable with explicit supersession metadata, never silently deleted.

## Acceptance tests to implement next
1. Source with missing integrity or provenance is blocked from promotion.
2. Duplicate/repeated evidence does not inflate mastery.
3. Contradiction remains unresolved until independently supported.
4. Held-out task failure lowers or suspends mastery; no self-certification.
5. Missing independent review is marked unavailable, not passed.
6. Proposed constitutional or permission mutation is rejected.
7. Cortex write failure leaves a durable pending receipt and does not claim persistence.
8. Replaying the same evaluation id is idempotent.
9. Historical authority conflict (Notion vs Cortex) resolves via dated effective policy, preserving older records.

## Rollout
Phase A: reconcile existing Knowledge Layer and promotion contracts, identify canonical interfaces. Phase B: implement versioned receipt schema and offline tests. Phase C: wire gated Cortex reads/writes and independent readback after authenticated access is proven. Phase D: optional scheduled/event-triggered evaluations with bounded budgets and stop conditions.

No live provider writes, autonomous scheduling, or mastery improvement are asserted by this document.
