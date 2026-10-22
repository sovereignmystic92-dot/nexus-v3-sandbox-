# Local implementation and validation — 2026-10-22

Implemented `SQLiteCoordinator` against the existing submit/resume interface. Each resume commits at most one transition. Artifact writes, checkpoint version changes and events share one SQLite transaction. A failed write raises an error and rolls back; it does not manufacture an INCOMPLETE checkpoint that was never persisted.

The caller supplies an explicit database path and a synthetic fixture catalog. Only exact catalog source/revision/hash matches and `synthetic:output` are accepted. Incomplete requests are held at NEW/BLOCKED, with no artifacts. Corrected incomplete sources require a new revision and idempotency key. A reused key with changed immutable fields raises BindingConflict. Repeated valid requests retain the original transaction/artifact identities.

At REGISTERED a separate SQLite connection checks all three artifacts: archive, output and local registry. Exact artifact IDs, transaction IDs, payload, destination and stored/computed SHA-256 must match. Failure preserves REGISTERED/INCOMPLETE with an explicit repair action. Existing conflicting artifacts are preserved. A successful verification is an immediate observation, not continuous integrity monitoring or a long-term durability promise. Terminal VERIFIED retries return that historical checkpoint without performing a new audit.

## Observed local result

Command: `PYTHONPATH=src python3 -m unittest discover -s tests/unit -v`

Observed: 14 tests collected and passed, no skips or failures. Tests used temporary SQLite files, cleaned by TemporaryDirectory. No external adapters, dependency installs or production operations were invoked by the test code. These tests ran in the available execution environment; full credential/filesystem/egress isolation was not independently established.

| Planned case | Local evidence | Remaining boundary |
| --- | --- | --- |
| S01 | Full progression and fresh-reader checks | Full run-envelope/reviewer attribution not implemented |
| S02 | Repeat and reopen retain artifact IDs | No cross-service duplicate proof |
| S03 | Changed hash/revision/destination/completeness rejected | Single local database only |
| S04 | Incomplete request stays BLOCKED without artifacts | No external source completeness assessment |
| S05 | Production destination denied before transaction insertion | No host routing isolation claim |
| S06 | Not implemented or tested | Historical/current authority resolver remains required |
| S07 | Instruction-like payload stored verbatim | No LLM or tool-execution boundary exercised |
| F01/F02 | Reopen after committed archive/output checkpoints | No process kill or torn external write tested |
| F03 | Tampered/missing/misrouted artifacts prevent verification; repaired payload can resume | No external adapter readback tested |
| F04 | Not implemented or tested | Local registry is not a reciprocal external endpoint |
| F05 | Forced event-insert failure rolls back artifact and checkpoint | Not disk-full, power-loss or filesystem failure proof |
| C01/C02 | Only stale checkpoint rejection tested | No concurrent workers, leases or fencing proof |

Additional tests reject unknown source/hash and false synthetic fixture markers, and preserve conflicting existing artifacts. The suite is deliberately reported as local unit/integration validation, not a completed AUD-40 acceptance run.

## Remaining work

Implement authority-conflict handling and claim attribution; emit complete attributable run envelopes matching evidence-schema.md; arrange isolated acceptance execution; validate concurrency only if expanding beyond one worker. Production Notion/Cortex adapters, hosting, scheduling, credentials and promotion are absent. Existing draft databases are incompatible with the added schema fields; use a fresh disposable database rather than silently migrating one.
