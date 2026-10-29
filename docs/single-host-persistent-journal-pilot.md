# Nexus single-host persistent journal pilot — deployment gate

Status: **DESIGN / NOT DEPLOYED**. PR #76 synthetic tests are not production evidence.

## Boundary

- Use one trusted, persistent host with a private, durable filesystem volume. Do not use the ephemeral checkout or runner filesystem of GitHub-hosted Actions as journal custody.
- Provision a dedicated non-root service identity and a private directory (0700), existing SQLite file (0600), same-host advisory lock, and stable absolute path. Provisioning is explicit, never an automatic recovery fallback.
- Pin the expected journal identity and exact source/target configuration. Never accept a journal merely because it exists.
- Mount the journal directory with backup/recovery policy appropriate to the host; backup evidence, fsync/power-loss survival and restore tests are separate gates. Avoid network filesystems with unreliable SQLite locking.
- No two hosts may share write custody. A second host, failover, or distributed worker requires externally enforced fencing/lease and verified handoff, not just SQLite or flock.
- Keep Notion and Cortex host callbacks absent or disabled for the pilot. No credentials, scheduled GitHub triggers, live API writes or production source data.

## Operator sequence (future host, not executed)

1. Provision host, service identity, private volume and durable journal path. Record host/volume identity and custody owner in the operator journal.
2. Explicitly initialize the sandbox runner once with a unique journal identity and fixture-only source/target bindings. Keep synthetic transport local. Do not initialize if the journal path or prior identity exists.
3. Stop the worker; run `python3 tools/journal_readiness_probe.py --journal /absolute/private/journal.sqlite --identity <expected-id>`. A HOLD verdict blocks recovery; a local observation alone never enables a write.
4. Start a separate process using the same host/volume and same exact identity/configuration. Verify one queued synthetic event reaches VERIFIED and a second recovery produces no duplicate effect.
5. Stop and restart the host service, then repeat independent readback; preserve file identity, journal contents and synthetic effect receipt.
6. Simulate an uncertain synthetic write acknowledgment and verify that recovery reconciles before retry; HOLD on ambiguity.
7. Simulate missing journal, wrong identity, unsafe permissions, and corrupted database. Require HOLD with no recreation, fallback or external writes.
8. Record process restart, service restart, host reboot, backup/restore and replacement-host results **separately**. Only observed results can close each gate.

## Explicit gates

| Gate | Evidence needed | Current status |
| --- | --- | --- |
| Synthetic cross-process reopen | Distinct Python processes share journal; duplicate synthetic effect prevented | CI passed on 42164ef |
| Private journal preflight | Existing path, mode, identity, SQLite quick_check | Synthetic CI passed |
| Dedicated host/volume | Named custody owner, volume lifecycle, permissions, non-root identity | NOT PROVEN |
| Service restart | Journal and synthetic receipt read back after service restart | NOT PROVEN |
| Host reboot | Journal and synthetic receipt read back after actual reboot | NOT PROVEN |
| Complete journal loss | Backup restore or external witness reconciliation without blind writes | NOT PROVEN |
| Multi-host fencing | Externally enforced exclusive lease/fencing | NOT PROVEN / OUT OF SCOPE |
| Notion checkpoint projection | Dedicated sandbox destination, independent write/readback | DISABLED |
| Cortex live bridge | Authorized scoped callbacks and independent readback | DISABLED |
| PASSIVE scheduled worker | Persistent-host custody, restart/recovery and explicit activation review | DISABLED |

## Stop conditions

Any identity/configuration mismatch, missing file, failed integrity check, lock conflict, uncertain effect, unavailable readback or unverified ownership means HOLD. Do not replace the journal, reinitialize it, enable a cron schedule, publish a canonical checkpoint or perform an external write merely to clear the failure.

## Next action

Select a real persistent host/volume under the operator's control, provision only the sandbox journal, and collect actual service-restart and reboot evidence before considering a schedule. This document does not authorize host provisioning or a live deployment.
