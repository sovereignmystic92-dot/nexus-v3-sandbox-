# Required-check protection verification — 2026-10-23

The owner configured [ruleset Main](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/rules/25721028) through GitHub. The assistant then fetched the saved policy and branch metadata. [Exact readback](branch-protection-observation.json) records the settings; it contains no credentials.

## Verified configuration

| Control | Saved value |
| --- | --- |
| Enforcement | Active |
| Branch target | Default branch; observed main |
| Pull request | Required |
| Approving reviews | Zero |
| Latest-push approval | Not required |
| Required CI | synthetic from integration 15368 |
| Up-to-date branch | Required |
| Force pushes | Blocked by non_fast_forward rule |
| Branch deletion | Blocked by deletion rule |
| Bypass actors | None; current connection reports never |
| Main branch metadata | protected=true |

This supersedes the earlier unprotected-main observation in PR #13. It addresses the configured merge-check enforcement gap without requiring a second person's review for routine solo merges. Zero required approvals does not satisfy or remove the foundation audit's independent human-review gate.

The policy is scoped to the default branch, rather than all development branches. Only the owner changed these administrative settings; the assistant performed readback. The connected API still does not provide general administration access.

## Candidate validation and limits

This evidence is being proposed through a documentation-only pull request after the rule became active. The candidate's workflow results and check-source association are recorded separately in the PR after observation. The configuration readback does not itself prove that every bypass path or a failing-check merge was tested; no deliberate unchecked merge is attempted.

The current frozen implementation baseline is `72e19fb232e4679e8d35b75f7f27381fedfaff7d`, through merged PR #13. Its actual main run passed 65 tests and four separately counted bounded coordinator faults. The three manual single-worker recovery cases and three C9 interleavings are separate evidence, not additions to that test count. This publication changes no runtime, test or workflow behavior.

No repository-wide webhook/app inventory, forced host cleanup, future retention/deletion, effective restricted identity, remote fencing, device/power-loss guarantee or human signoff is established by branch protection. Single-worker synthetic scope remains mandatory. Full foundation acceptance stays BLOCKED; Notion remains authoritative and paused.
