# Nexus foundation audit sandbox

Public, synthetic-only repository: `sovereignmystic92-dot/nexus-v3-sandbox-`.

**Full foundation acceptance remains BLOCKED.** Main now includes the coordinator, four mission scenarios, Cortex adapter and identity-history safeguard. Notion remains authoritative; its integration stays paused. No production deployment or canonical promotion follows from these results.

Start with [the current foundation audit status](docs/foundation-audit-status.md), verified through merged PR #8. The actual main run passed **63 tests and four separately counted bounded coordinator fault checks**. Historical documents retain earlier counts and observations; the status document separates those from current evidence and lists the remaining gates.

## Reproduce offline tests

Python standard library only:

```sh
python3 tools/validate.py --output local-validation.json
```

Tests use temporary synthetic databases and offline transports. This command does not call Cortex or Notion or establish host isolation.

The GitHub workflow uses credential-free public source acquisition and a digest-pinned, network-disabled test container. The workflow covers main and selected development-branch pushes plus PR merge candidates targeting main/mission-scenarios. PR #2 is merged and its actual main-push run passed 32 tests plus four bounded faults. PR #4 is also merged, and its actual main-push run passed 52 tests plus four bounded faults. See [CI coverage](docs/ci-coverage.md) for earlier milestones and [current audit status](docs/foundation-audit-status.md) for the later PR #8 baseline.

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
