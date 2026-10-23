# Nexus foundation audit sandbox

Public, synthetic-only repository: `sovereignmystic92-dot/nexus-v3-sandbox-`.

This Cortex review branch contains a single-worker Python/SQLite coordinator, four synthetic mission scenarios and a Cortex persistence adapter. **Full foundation acceptance remains BLOCKED.** Notion remains authoritative; Notion integration is paused. No production deployment or Nexus promotion follows from these results.

Start with [the current acceptance review and merge order](docs/current-acceptance-review.md). Historical documents retain earlier test counts and unverified states; that current review consolidates the later evidence and its limits.

| Scope | Observed status |
| --- | --- |
| Synthetic coordinator and missions | 32 tests on PR #2, including four mission cases |
| Cortex adapter branch | 52 tests total, including 20 adapter/bridge cases; hosted run passed |
| Bounded coordinator faults | Three SIGKILL checks and one dedicated 4 MiB ENOSPC check passed, counted separately |
| Live Cortex adapter | Three fixture creates, duplicate-free reconciliation/restart, v1→v2 update, uncertain v2→v3 update recovery across restart and stale-target blocking verified |
| Notion adapter | Separate paused draft PR #3; not included in this branch |
| Production, multiworker fencing and independent audit | Not established |

## Reproduce offline tests

Python standard library only:

```sh
python3 tools/validate.py --output local-validation.json
```

Tests use temporary synthetic databases and offline transports. This command does not call Cortex or Notion or establish host isolation.

The GitHub workflow uses credential-free public source acquisition and a digest-pinned, network-disabled test container. The proposed workflow covers main and selected development-branch pushes plus PR merge candidates targeting main/mission-scenarios. PR #2 is merged and its actual main-push run passed 32 tests plus four bounded faults. PR #4 is also merged, and its actual main-push run passed 52 tests plus four bounded faults. See [CI coverage](docs/ci-coverage.md).

## Review evidence

- [Mission scenarios and evidence](docs/mission-acceptance.md)
- [Cortex adapter contract and live observations](docs/cortex-adapter.md)
- [Hosted 52-test report](docs/hosted-run-39881697563.json)
- [C05 live creation/recovery result](docs/cortex-c05-live-result.json)
- [C06 live update/conflict result](docs/cortex-c06-live-result.json)
- [Runner, fault and retention limits](docs/review-and-fault-checks.md)

C05 records historical version-1 observations; C06 advanced its synthetic registry to version 2; C11 advanced the same fixture to version 3 and verified uncertain-update recovery. The old probes must not be blindly replayed as current acceptance commands. Live callbacks remain host-mediated and opt-in; this repository installs no unattended integration or credentials.

PR #2 is merged into main at `08464ae2a7f169bf37a569ecf9e6766da9e3d50f`; [main run 39888300351](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39888300351) passed. PR #4 was subsequently merged at `62265e0d5bf3f371b965eab7f953dc9230501eaf`; [main run 39889605147](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39889605147) passed 52 tests and four bounded faults. Keep PR #3 paused. See [merge follow-through evidence](docs/pr2-merge-followthrough.json).

## C11 uncertain-update recovery follow-through

[The C11 probe](docs/cortex-c11-probe.py) exercised the unchanged adapter against one bounded synthetic update, then a separate read-only reconciliation process. The writer made one update and reported uncertainty after a deliberate local acknowledgment discard. The restarted process verified exact v3 state with 11 reads and zero writes, repeated verification without mutation, and blocked a stale v2 baseline. See [the result and limits](docs/cortex-c11-live-result.json). This review adds probe/evidence documents only; it installs no live automation.
