# Nexus historical observation continuity — rollout gate

Status: **NOT ENABLED**. This document describes the intended safe path,
not evidence of an unattended historical recovery.

## Existing controls

- The daily workflow runs with `permissions: {}` and does not access
  `GITHUB_TOKEN` for historical downloads.
- PRs #324–#328 provide snapshot reconciliation, metadata validation,
  authenticated transport components, and a supervised recovery entrypoint.
- `module_evolution_history_selector.py` rejects failed or incomplete
  immediate predecessors rather than silently skipping history.
- An empty or truncated GitHub API listing must never be interpreted as a
  trustworthy first-run bootstrap.

## Required before enabling

1. Provision a narrowly scoped, **read-only Actions** credential for this
   repository through an approved GitHub secret or short-lived GitHub App
   token. Do not put a token in code, artifacts, logs, or pull requests.
2. Add authenticated GitHub workflow-run discovery and pagination, with a
   verified first-run/bootstrap anchor. The selector in this PR is offline
   and does not make network calls.
3. Verify the actual archive redirect host against GitHub's live endpoint
   before relying on the existing transport host allowlist.
4. Validate source run, attempt, repository, workflow path, main branch,
   artifact ID, archive SHA-256, checkpoint digest, and receipt continuity.
5. Change the scheduled workflow only after its workflow-policy fingerprint
   and branch protection checks are updated. Keep `permissions: {}` if
   using a separately scoped credential; do not silently grant broad
   `GITHUB_TOKEN` access.
6. Prove **two separate real GitHub Actions runs**: the second checkpoint
   contains both its own observation and the first run's observation.
   Publish the evidence and read it back independently.
7. Preserve the existing no-Cortex-write and no-readiness-promotion rules.

Until all gates pass, the scheduled workflow continues to produce
single-run observations, and the continuity capability is not live.
