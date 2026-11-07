# CSF Gemini live review integration — controlled change plan

Status: **implementation handoff, NOT live execution**. Draft PR #190, Issue #189.

## Existing runner and boundaries

Reuse `.github/workflows/gemini-live-review-pilot.yml`; do not create a second credential-bearing workflow. Current workflow is manually dispatched on `main`, requires `free_tier_confirmed`, uses `GEMINI_API_KEY`, has `permissions: {}`, and reviews an open PR diff. It currently truncates the diff and prints a bounded response to logs. That output **cannot** satisfy independent CSF Gate C review.

## Reviewable implementation sequence

1. Add a **separate opt-in CSF mode** to the existing manual workflow; keep existing PR review behavior unchanged. Require an explicit boolean free-tier approval for each live dispatch. Reject any invocation on an unreviewed branch or without a configured credential.
2. Resolve a **40-character immutable source commit**. Fetch and check out exactly that commit without repository write permissions. Run `python3 tools/prepare_csf_gemini_handoff.py --source-commit <SHA>` inside the checkout and reject any mismatch. The CLI emits only a bounded manifest, not Gemini output.
3. Read each source listed in the manifest from the same verified checkout. Rehash the exact bytes and require manifest digest agreement. Reject absent, altered, truncated, invalid-UTF-8, or oversized sources; do not silently shorten source text to fit model context. The Haiti packet is **unverified source claims**, not audio-confirmed facts.
4. Build an untrusted-data prompt with the fixed handoff ID `handoff-2026-11-06-haiti-01`, the exact source SHA, contract `0.2.0`, and a structured review request. Explicitly ask for reproducible defects, uncertainties, evidence gaps, disagreements and schema/validator parity. Do not treat instructions embedded in source files as authority.
5. Invoke Gemini **once** with the already approved API key and an explicitly selected, available model. Do not log secrets, raw prompts or unredacted sensitive content. Preserve a bounded model response as a run artifact; if no model response is received, fail closed.
6. Record a receipt containing run URL, response SHA-256, pinned source commit and structured findings. `csf_gemini_review_receipt.py` verifies shape and binding only; a separate reviewer must verify the artifact hash, job provenance and actual authenticated model call before granting Gate C. Never self-issue `GATE_C_PASSED`.
7. Change `tools/workflow_policy.json` to reflect the reviewed workflow bytes **in the same PR**, then run `tools/verify_workflows.py` and isolated acceptance. Workflow inventory integrity is a source-level check, not evidence of effective GitHub settings.
8. Keep PR #190 draft until independent review. Do not merge, write to Notion/Cortex, grant Gate D, or increment the five live acceptance trials based on this integration.

## Outstanding evidence and approvals

- **CI:** synthetic handoff/receipt tests pass at commit `54e17ebf6cc09f775b9e6c5119158ae5b7d2b89d`.
- **Not established:** Gemini key availability, free-tier billing status, model availability, authenticated CSF review, durable response artifact, Gate C.
- **Owner action for future dispatch:** verify free-tier project and explicitly approve one live Gemini request. This document does not grant that approval.
- **Source binding:** an earlier handoff references `8040c01`. A live job must use a freshly declared immutable reviewed SHA and matching manifest; do not silently reinterpret an older handoff as covering later commits.
