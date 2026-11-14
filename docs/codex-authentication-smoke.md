# Codex runner authentication smoke test

## Evidence and scope

[Readiness run 43517848871](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/43517848871) verified the assignment and checkout at `4df657d2028623313866e55ec677ab388d72156f`. Its artifact reports `BLOCKED_CODEX_INTEGRATION_UNVERIFIED`. This proposal tests authentication only, separately from assignment implementation and the Cortex write safeguard.

## Proposed execution

- Use a GitHub-hosted Linux runner and a manually dispatched workflow on the trusted default branch. Bind the dispatch to a repository-owned approved revision and allow one active run. Set a five-minute job timeout and require explicit cost authorization before the model invocation.
- Use the official [Codex GitHub Action](https://learn.chatgpt.com/docs/github-action) pinned to a reviewed immutable release commit. Use the documented `openai-api-key` input via a protected GitHub environment secret. Verify that an approved OpenAI project credential and spending terms are available before deploying. A GitHub connection or ChatGPT session alone does not demonstrate API authentication from the Actions runner.
- Run in a clean workspace with a fixed, non-sensitive prompt asking for one literal success marker. Use the action's read-only sandbox with `drop-sudo`, no Cortex or Notion connector, and empty GitHub token permissions. No repository checkout, changes, or agent-controlled instructions are needed for the authentication test.
- Save the model output to a temporary file. Require a successful action exit and an exact match to the fixed marker. Publish only normalized status, run ID and attempt, workflow revision, pinned action revision, and marker-match boolean. Keep raw output and provider errors out of the receipt. Any failure blocks promotion and preserves the failed stage. Verify the artifact independently.
- The workflow inventory currently rejects every unregistered workflow, requires empty GitHub token permissions, and compares provider secret references against an explicit routing allowlist. Any executable implementation must update the inventory and credential-routing rule for this exact file and environment in the same reviewed PR.

## Acceptance and rollback

An authenticated pass requires a real provider-backed action invocation, exact marker match, and independently downloaded receipt. Missing credentials or authorization, action failure, and wrong output must never produce a passing receipt. An authenticated pass leaves the Cortex research issue and the unattended transcript count outside its scope. Disable the smoke workflow and remove its environment secret binding to roll back. No credential, spend, or launch is authorized by merging this design.
