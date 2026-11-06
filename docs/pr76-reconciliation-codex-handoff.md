# PR #76 reconciliation — Codex execution handoff

This document is **instructions**, not evidence that a merge or test passed.

## Scope and baseline (verified at handoff preparation)
- Repository: `sovereignmystic92-dot/nexus-v3-sandbox-`
- Original PR: #76, draft; original head `e122371f07915cc0b6fd4effa94392c1af5b5d4a`; **DO NOT MODIFY original PR branch** `cortex-primary-authority-20261028`.
- Work branch: `reconcile-pr76-main-sandbox-20261105`, created from that same original head. This handoff document itself is an additional commit on the work branch.
- At last check, GitHub reported the PR as not mergeable, and the work branch and `main` diverged. This document is not a merge-conflict-resolution.
- Never merge to `main`, modify secrets/billing, activate schedules, deploy, write to live Notion/Cortex, or provision deferred host D26.

## Safe execution sequence
1. Clone/fetch both remote heads in an authenticated work environment and verify their exact SHAs. Never assume `main` is unchanged. Refuse dirty checkout or mismatched target ref.
2. Ensure the current branch is `reconcile-pr76-main-sandbox-20261105` and create a rollback ref before merging.
3. Merge `origin/main` into that work branch with `--no-commit` initially (do not push or finalize the merge until all conflicts are examined).
4. Inspect every unmerged file with `git diff --name-only --diff-filter=U`. An earlier per-file comparison found only `tools/workflow_policy.json` modified on both sides; **that is not proof it is the only actual merge conflict**.
5. The common workflow-policy entries have identical hash values. The PR branch adds `nexus-passive-synthetic-pilot.yml` and `main` adds eight other workflow files. Preserve the full matching workflow inventory, security constraints and hashes; do not simply copy a policy without the workflow files.
6. Check `tools/verify_workflows.py` and `tools/verify_ci_source.py` contract/credential controls, plus all other overlapping files and tests. Resolve conflict markers and review final diff before commit.
7. Validate Python/JSON syntax; run `python3 tools/verify_workflows.py`, repository's CI policy checks, `tests/unit/test_agent_routing.py`, `tests/unit/test_routing_journal.py`, journal recovery and isolation tests. Run full `python3 tools/run_isolated.py` only in its intended trusted GitHub runner context with correct environment and Docker, not by faking source/retention assertions.
8. If tests fail, stop or fix on **work branch only**. Log explicit pass/fail/blocked output and exact SHA. Push only the test branch when safe. Verify fresh GitHub Actions checks against that SHA.
9. Do not update original PR #76 until reviewed reconciliation is accepted; never merge original PR to main here.

## Success requirements
- Original PR branch and `main` unchanged.
- Every workflow file matches SHA-256 policy and credential/permission review.
- Routing/journal tests pass, stale or duplicate proposals HOLD as designed.
- New branch CI starts and succeeds; any missing result is **UNVERIFIED**.
- No operational status/audit checkpoint is upgraded solely because code or documentation was committed.

## Reporting
Provide branch SHA, merge-base and merged-main SHA, conflicts encountered and chosen resolutions, files modified, exact test invocations, independent CI URLs, and remaining restrictions.
