# Codex execution trigger — implementation contract (proposed, not deployed)

Status: **DESIGN ONLY / NOT AN EXECUTABLE CODEX TRIGGER**. This document accompanies PR #307; it does not authorize or dispatch any agent, Cortex write, or workflow.

## Objective

Allow an authorized GitHub Actions worker to take a single approved implementation assignment and hand it to an **actually configured** Codex runner. The runner must create a reviewable code change, not write to Cortex. First candidate: the single-writer safeguard described in PR #307 comment 6860897547.

## Preconditions (fail closed)

1. Inventory existing Actions workflows, runner availability, GitHub App permissions, Codex CLI/service integration, authentication mechanism and permitted costs. Verify the integration using an approved read-only preflight; do not assume a PR comment invokes Codex.
2. Require a repository-owned allowlist of permitted assignment IDs and exact PR/head SHA. A comment, label, or issue body alone is untrusted input and **never** authorizes code execution.
3. Require explicit owner authorization for each dispatch and least-privilege runner credentials. Do not accept pull-request-origin secrets or execute untrusted fork code with write tokens.
4. Enforce one active job per assignment using GitHub Actions concurrency plus durable reconciliation. Concurrency alone does not prove provider-side Cortex single-writer safety.

## Proposed execution sequence

- Authorized manual `workflow_dispatch` on the trusted default branch accepts an allowlisted assignment ID and expected SHA; verify both against repository-owned configuration.
- Preflight verifies runner identity, installed Codex integration, granted GitHub scopes, and available budget; fail with a redacted blocker if absent.
- The worker starts Codex using the documented, approved integration, in a sandbox without Cortex credentials or write permission. No placeholder command should be treated as a real invocation.
- Codex checks out an isolated branch, implements the single-writer safeguard and deterministic tests, and opens or updates a reviewable PR. It must not merge, trigger Cortex, or mark audit gates passed.
- CI records exact run ID, head SHA, test evidence, artifact digest, and failures. Gemini independent review is a separate explicitly authorized stage, not implied by passing CI.
- A durable redacted completion receipt is written to the existing Nexus audit thread only after deduplication; missing receipt is a separate blocker, not a reason to rerun implementation blindly.

## Required test cases

Unauthorized event; stale SHA; duplicate dispatch; parallel assignment requests; missing runner identity; missing Codex integration; missing/insufficient token scopes; cancelled job; partial commit; repeated delivery; failed CI; failed audit receipt; hostile issue text. Verify no Cortex access and no silent gate promotion.

## Promotion conditions

An implementation is *operational* only after a real Actions run shows an actual Codex invocation, code commit/PR, tests and durable receipt. Separately, the Cortex research pilot remains blocked until provider-supported atomic conditional update or a demonstrably enforced single-writer/fencing path is independently verified. No direct GitHub-runner Socra authentication is required for the separate Chat-mediated transcript route.

## Current blocker

`CODEX_DISPATCH_INTEGRATION_UNVERIFIED`: the repository branch and assignment comment exist, but no verified installed Codex runner/dispatch path has been identified. Owner or Codex must establish an authorized integration before executable workflow deployment. Avoid storing secrets in issues or this document.
