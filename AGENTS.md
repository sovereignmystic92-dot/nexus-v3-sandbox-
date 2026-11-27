# Nexus engineering agent instructions

These instructions apply to Codex and other coding agents working in this repository. Read the repository's existing Nexus constitution, policies, audit requirements, and relevant workflow documentation before making changes. More restrictive existing rules prevail.

## Roles and handoffs
- ChatGPT is the human-facing coordinator: scopes missions, tracks evidence and blockers, and requests owner decisions.
- Codex is the implementation and maintenance engineer: investigates code, writes bounded changes, tests, diagnoses CI failures, and prepares reviewable pull requests.
- Gemini may perform research and independent review where configured and authorized. Do not claim that Gemini was consulted without an actual recorded review.
- GitHub Actions is the execution and evidence engine. A successful offline/synthetic test does not establish live provider access.
- Notion is the canonical archive for original transcripts, source links, versioning, and provenance. Cortex owns derived analytical outputs. Do not silently substitute one store for the other.

## Operating rules
1. Work only within the explicitly authorized task and existing repository controls. Prefer a feature branch and draft PR for integration changes. Do not merge, deploy, or change external provider records without separately verified authorization.
2. Never bypass OAuth, permissions, approval gates, audit logging, identity checks, or rate/cost limits. Do not put credentials, bearer tokens, or secret values into source, comments, logs, issues, or PR descriptions.
3. Fail closed on missing or ambiguous credentials, installation identity, module grants, or external service responses. Do not invent API endpoints, grant types, OAuth token contracts, scopes, or successful results.
4. Distinguish **offline**, **synthetic**, **authenticated read-only**, and **live write** evidence in every report. Only mark a checkpoint passed when its stated evidence requirements are actually met.
5. Before proposing changes, inspect relevant workflows, code, and test contracts. Run the narrowest useful tests, then applicable broader validation. Record exact commands, outcomes, and any tests that could not run.
6. Preserve existing production settings, existing secrets, provenance, idempotency, and retry/reconciliation guarantees. Minimize changes and keep an explicit rollback path.
7. For unattended or triggered work, use bounded missions, least-privilege GitHub permissions, concurrency/idempotency controls, durable receipts, and explicit stop conditions. An agent prompt or GitHub issue alone is not proof that an unattended Codex runner is installed.
8. Do not self-certify independent review. Surface unresolved blockers and exact human actions required.
9. For new qualifying transcript processing, use `execute_supervised` with a complete `analysis_gate`, or its CLI with the same sidecar. Missing evidence is a blocker; do not replace the entrypoint with generic pipeline/handoff primitives to bypass it. Older ungated journals may use only the separately authorized `reconcile_legacy_supervised` provider-read-only recovery with reason/evidence recorded; never reset a journal to remove a hold. This guidance does not install automatic invocation in arbitrary Chat sessions.
10. Existing-output enrichment uses only the Python `execute_supervised` append mode described in `docs/transcript-supervised-update.md`, with a complete final-content analysis gate, exact baseline, stable enrichment ID, retained operation journal and host-verified exclusive mutation custody. `allow_update` and an evidence reference do not prove permissions or custody. Do not turn its baseline/version pins into an unsupported claim of provider CAS or remote fencing; no update CLI or live dispatcher is installed. Preserve source, prior analysis, relationships and prior transaction journals.

11. Ordinary owner-invoked single-writer transcript creates may use `execute_checkpoint_supervised` under `docs/checkpoint-supervised-host.md` after an operation-specific host-verified exclusive assignment. Retain/read exact pre-effect intent and post-effect receipt in the authorized Cortex checkpoint while preserving the native journal and complete analysis gate. Missing local journals HOLD; never reconstruct or reset intent. Scheduled invocations do not qualify, and this exception does not relax rule 10 or authorize append updates, parallel workers, remote takeover or unattended acceptance.

12. A confirmed pre-dispatch INTENT may continue once through `recover_checkpoint_supervised` under `docs/pre-dispatch-recovery.md`, only after exact owner/code/evidence review and host-verified exclusive supervised assignment. Preserve the original transaction, binding, native INTENT and retained intent; consume one recovery permit in the same journal and retain separate recovery events. Destination absence alone, an uncertain provider outcome or a lost journal cannot qualify. A consumed/started recovery is read-only reconciliation only. No append exception or unattended authorization is granted.

13. ChatGPT may use its authenticated Cortex connector for an owner-invoked batch of up to three named, new transcript analysis modules. This is an exception to rules 9 and 11 for these creates. The owner explicitly approves the source and destination pairs. Use the Chat–Cortex bridge's read-before-write and independent readback pattern. This route dispenses with the supervised host, native journal, host-verified assignment and bridge GitHub issue packet for these creates. Process one source at a time.
    - Verify that the hourly worker excludes publication of each approved source for the duration of the batch. Confirm the authenticated account and destination parent. Read the canonical Notion capture, verify its pinned revision and SHA-256, and bind them to the final analysis. A capture with a documented cutoff qualifies only if the owner accepts the exact supplied scope and the missing portion does not block a required analysis determination. Preserve the raw capture and its actual completeness status. Evaluate material domain coverage, source citations, uncertainty, dependencies and required processing actions under existing quality rules.
    - Record the source ID, revision and digest, fixed destination name, final content digest, and intended dependencies in the session before dispatch. Check the exact destination name and search by source page and video identity for prior outputs and unresolved intent. Reconcile an exact existing result by readback. Stop the affected item if source, destination or prior attempts are inconclusive or conflict.
    - Send at most one create for that source and revision at the fixed account-unique destination name. If the outcome is uncertain, use read-only reconciliation of that destination and retain the unresolved result. Absence after uncertainty does not authorize another create. Independently read back the source binding, module ID, owner, parent, dependencies and exact saved content. Record the verified module ID, version and content digest before counting the item as newly published. Record capture completeness and analysis completion separately. Existing verified outputs may be linked into Knowledge Mastery by its normal writer after reconciliation.
    - Existing-output enrichment, held transaction recovery, scheduled publication and foundation audit acceptance continue under their applicable rules. The verified Generation Ships v1 result remains the first pilot receipt.

## Standard engineering handoff
For each Codex task, report:
- Goal and owner authorization
- Files changed and PR/commit references
- Tests run, with passed/failed/not-run results
- Evidence classification (offline/synthetic/authenticated read-only/live write)
- Security and permissions implications
- Remaining blockers and next owner action

## Current CP05 constraint
PR #210's Cortex workflow must not be treated as authenticated success until the OAuth installation identity (client, project, authorized principal, and effective `module.view` on the intended module) is established and the token exchange contract is verified. Do not store a short-lived access token as a permanent GitHub secret. Keep the PR in draft until verification and workflow checks pass.

## Activation limitation
This file configures repository instructions for Codex when Codex is invoked on the repo. It does not itself install a Codex GitHub Action, grant repository access, create a scheduled task, or cause Codex to run automatically.
