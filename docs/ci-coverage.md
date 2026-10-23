# Main and pull-request CI coverage — C08

The workflow now runs on pushes to main, foundation-audit-draft, mission-scenarios and cortex-adapter, and pull requests targeting main or mission-scenarios. PR activity types are opened, synchronize, reopened and ready_for_review. Both event scopes have no path filters, so documentation-only changes also get a result instead of leaving an expected check pending. Concurrency is separated by event and ref; a branch push does not cancel its PR run or another branch's validation.

The same workflow was added to PR #2 and PR #4. This lets the first planned merge install main coverage and gives the mission baseline its own PR merge-candidate validation. PR #3 remains paused; its implementation was not edited.

## Exact candidate verification

SOURCE_SHA uses GitHub's event SHA. For pull_request, SOURCE_REF must match refs/pull/NUMBER/merge, and the fetched commit's raw parent list must equal the event's base SHA followed by head SHA. The runner verifies its checkout equals SOURCE_SHA. The workflow prints structured ci_source evidence, and the isolated runner separately records source_commit and file hashes. A source-branch-only run cannot satisfy the PR parent check.

A shallow fetch retains raw commit parent headers; the check uses git cat-file rather than ancestry traversal through the shallow boundary. No pull_request_target or privileged checkout action is used. Official behavior reference: [GitHub pull_request events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request).

## Observed runs

| Scope | Run | Exact tested source | Tests | Separate faults |
| --- | --- | --- | --- | --- |
| PR #4 source push | [39886975124](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39886975124) | `855ab4ecf8fcc778fe093b1e39b5383206494012` | 52 passed | 4 passed |
| PR #4 merge candidate | [39886978646](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39886978646) | `6358298740397258b331f603d706210fad2b897b` | 52 passed | 4 passed |
| PR #2 source push | [39887166538](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39887166538) | `d9a5b7d45ec14c50ee11897f227fe31806dd0c67` | 32 passed | 4 passed |
| PR #2 merge candidate | [39887170938](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39887170938) | `38fb47fa52eb6f1f99e8bc166a526fe0d1d38283` | 32 passed | 4 passed |

Completed job logs were retrieved and parsed. Both PR runs passed the exact base/head parent check. All four runs reported passing host/container boundaries, source-manifest comparison, four mission cases, bounded fault checks and ordinary container/staging cleanup. Log retention was reported as 90 days. [Structured evidence](ci-coverage-results.json) preserves the reports except repeated coordinator sample-attempt envelopes, with the omission identified explicitly.

The recorded PR #4 candidate predates the workflow backport to PR #2. Publishing these docs creates another PR #4 synchronize event; its new candidate must pass against the updated mission-scenarios base before the final completion record is made. Later run IDs and base/head verification are retained in the scoped Cortex C08 evidence issue; they are not retroactively assigned to the historical sources above.

## Limits and merge handling

- Main remains unchanged. Its push event is configured in the proposed workflow, but no actual main push is claimed. After an approved PR #2 merge, observe the resulting main run before advancing the merge sequence.
- PR #2 then PR #4 remains the order. After PR #2 merges, retarget/re-read PR #4's base and require a fresh PR merge-candidate run. Current success against mission-scenarios is not future success against a changed main.
- This change creates CI checks; it does not install branch protection, require checks administratively, mark drafts ready or authorize a merge.
- Permissions remain empty, acquisition remains public and credential-free, and tests remain in the digest-pinned, nonroot, resource-limited network-none container. There is no deployment, schedule or live connector invocation.
- Fork PRs may require GitHub's normal workflow approval; merge conflicts cannot produce a valid PR merge-candidate run. A missing/blocked run is not a pass.
- Full foundation acceptance remains BLOCKED. Notion integration remains paused.

Local validation covered YAML/event scopes, empty permissions, Bash syntax and embedded Python compilation. Hosted execution supplied the substantive behavior checks; no implementation-mirroring unit tests were added.
