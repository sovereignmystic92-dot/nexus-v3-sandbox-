# Authority resolution and acceptance follow-through — 2026-10-22

## Implemented local authority contract

`authority.json` contains one explicitly synthetic current policy. The resolver accepts structured documents labelled current, historical, source or hypothesis, with IDs and revisions. Only current documents govern. Missing authority, conflicting current rules and explicit denial fail closed at NEW/BLOCKED before artifacts exist. Malformed or duplicate identity metadata is rejected. The harness supports only allow/deny for synthetic output; prose cannot grant privileges or add a production destination.

Historical, source and hypothesis documents remain in attempt provenance even when their rule contradicts current authority. They do not override current authority. The governing revision is bound to each transaction. A changed governing revision or denial during recovery holds the last checkpoint and preserves existing artifacts. Restoring the original bound current policy permits recovery of such a hold. Initially blocked submissions require a new key after resolving authority; incomplete source corrections also require a new source revision. Labels come from the operator; the resolver does not authenticate authors, infer real-world authority, or parse arbitrary Nexus documents.

## Attributable local evidence

Every committed state transition now writes an attempt envelope and its referenced event atomically with the checkpoint/artifacts. Envelopes include all fields required by evidence-schema.md: code/fixture hashes, runtime label, timestamps, operation outcome, protocol verdict, confirmed checkpoint, next action, exact artifact IDs, expected/readback hashes, fresh-reader identity, authority provenance and limitations. A failed verification remains recorded after later repair. A failed event write rolls back the checkpoint, artifact and attempt together; it raises an exception and does not claim durable failure logging to an unavailable database. Repeated submissions and terminal reads return existing checkpoints rather than inventing new attempts.

The code revision is a SHA-256 of package source files, not a guessed Git commit. The validation report also hashes test and runner sources. Runtime identity is an explicit synthetic label, not verified credentials or independent operator identity. No claim-level semantic attribution or natural-language authority reasoning is implemented.

## Observed results

24 distinct local tests passed with no skips, failures or duplicate test IDs. All seven S01–S07 scenarios now have local test coverage, including S06. This covers the fixture-based contract only. `docs/validation-results.json` contains reproducible test statuses, file hashes and seven actual synthetic attempt envelopes (six successful progression checkpoints plus one authority-conflict hold).

Reproduce with Python standard library only:

```sh
python3 tools/validate.py --output local-validation.json
```

The runner uses disposable temporary SQLite files and removes them. No external adapters, hosting or paid services are invoked. Its successful exit code means the local suite passed; the JSON separately retains full_acceptance_status=BLOCKED.

## Full acceptance verdict: BLOCKED

A bounded attempt to create a user/network namespace returned `unshare: write failed /proc/self/uid_map: Operation not permitted`. The installed bubblewrap alternative also failed: `bwrap: loopback: Failed to create NETLINK_ROUTE socket: Operation not permitted`. Docker, Podman, nsjail and firejail executables were not present on PATH. No escalation was attempted. Tests were therefore run as local unit/integration checks in the available host, not as an isolated acceptance run.

C1–C4 and C8 still lack the required host/identity/credential/egress/teardown evidence. A separate reviewer and retention arrangement are also unresolved. Full acceptance requires a host that can establish these controls; application-level routing checks cannot substitute for them. The validation runner does not probe or assert isolation automatically.

F01/F02 cover reopening committed checkpoints, not process-kill or cross-service partial-write recovery. F03 covers local artifact mismatch and repair. F04 external reciprocal endpoints remain absent. F05 tests rollback using an injected SQLite event failure, not full disk or power loss. C01/C02/C9 remain outside the single-worker implementation: stale checkpoint rejection is not lease fencing. Notion remains authoritative; no Nexus promotion, production modification, merge or deployment follows from this report.

## Resolution path

Continue local implementation and review under the current limited verdict. Before full acceptance, use a disposable runner with independently checked filesystem/identity isolation, no production credentials or mounts, enforced network denial during tests, and verified stop/cleanup and retention. An administrator-supported host configuration can supply those capabilities; changing a policy flag in this application cannot. No new runner, account, workflow, cloud resource or spending has been provisioned.
