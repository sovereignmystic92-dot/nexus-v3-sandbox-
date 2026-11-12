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
