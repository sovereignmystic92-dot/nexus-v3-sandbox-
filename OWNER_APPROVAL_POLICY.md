# Owner delegation: independent two-AI approval

Authorization date: 2026-10-28 (America/New_York).
Policy version: owner-two-ai-production-2026-10-28.

## Owner decision

In the current conversation, the owner explicitly confirmed that independent two-AI review may authorize Nexus production deployments and routine writes without additional routine human sign-off. Permission expansion, credential changes, and destructive actions still require explicit owner approval. Provider and platform requirements remain binding.

This broadens the prior sandbox-only delegation. Production authorization is conditional on the review and applicable technical requirements below; it is not an instruction to deploy immediately.

## Review procedure

Two identifiable AI reviewers independently inspect the same exact revision, requirements, proposed operation, destination, and relevant configuration. Each records its initial findings before receiving the other's conclusions. Identify sessions and available model identities, and disclose shared model families and any prior exposure to the other review.

Both reviews require evidence-backed dispositions, relevant test results, scope exclusions, and a clear verdict. Agreement alone is insufficient. Compare findings afterward, resolve material issues, and verify fixes against the final revision. Material changes invalidate affected approvals and require renewed review. Missing evidence or unresolved material disagreements hold the affected operation.

The implementing author's assertions do not substitute for independent review. If two independent reviewers are unavailable, this authorization condition is unmet.

## Scope and remaining requirements

The delegation replaces routine owner sign-off for production deployments and routine writes once its conditions are met. It does not waive technical checkpoint requirements, stale-write protection, cleanup/retention requirements, or actual provider/platform controls. Existing production-paused statements are superseded only as a requirement for routine human authorization; technical readiness must still be demonstrated for the specific operation.

Permission expansion, credential changes, and destructive actions require owner approval even when embedded in an otherwise routine deployment or write. Do not infer permission to expand destinations or access from this policy.

Persist attributable review records and operation evidence with revision, scope, destination, verdict, and findings disposition. Record actual outcomes and read-back where applicable. Do not mark any checkpoint passed merely because this delegation exists.

## Adoption status

This file records the owner's explicit authorization. It does not claim the review workflow has been implemented, that CP10 is closed, or that any deployment has occurred. Reconcile the checkpoint definitions, register, operational instructions, and pending PR #52 with this version before claiming repository-wide enforcement. Preserve earlier definitions and evidence as dated history.
