# Sandbox mission decision journal — local durability boundary

Status: **SYNTHETIC ONLY / NO LIVE WORKER**. Draft PR #76.

## Design

- `mission_dispatcher.dispatch` is a pure trigger/dependency/step decision. It never executes steps.
- `MissionJournal.provision` explicitly creates a separate private SQLite journal file. A missing journal is not automatically reconstructed.
- `MissionJournal.record` stores a canonical mission contract, caller-supplied trigger/dependency/verification evidence, a deterministic decision, expected revision, and a linked SHA-256 history entry in one SQLite transaction; it performs a separate local readback.
- `MissionJournal.observe` reopens the existing file with the declared identity and validates local schema, database quick-check and the mission's revision chain.
- Duplicate identical decisions do not create a new revision; concurrent/stale writers must present the current revision; changed mission contracts require a different mission ID.
- Recorded evidence cannot be silently retracted; removing a blocked state requires an explicitly designed reconciliation workflow, **not** a manual database edit.
- All step verification evidence is supplied by a trusted future caller; **this component does not authenticate that evidence**. Hashes reveal accidental/local modifications under normal assumptions but are **not an external tamper-proof witness**: an attacker able to rewrite all local journal content and hashes can evade detection.
- A READY result is a **non-executing proposal**, never write authority. COMPLETE means supplied step evidence covers the bounded mission contract; it does not establish that a live external action succeeded.

## Current synthetic evidence

Tests cover reopen across separate processes, revision replay/idempotence, progress recording, HOLD preservation, missing-file failure, wrong identity, scope changes, unsafe permissions and local history tampering. These tests use ephemeral local CI storage, not a deployed durable host.

## Explicitly not enabled

No webhook subscription, event watcher, background research loop, external executor, Cortex or Notion writes, schedule, production journal, independent verification service, backup/restore, host reboot, multi-node fencing, or cross-machine persistent storage.

## Future gates

1. Authenticate trigger observations and authorize any requested executor separately.
2. Add bounded step execution, independently verify receipts, and record those proofs through a trusted host.
3. Define an explicit reconciliation event for blocked decisions before allowing a cleared HOLD.
4. Exercise crash-injection and concurrent writers, source-staleness, journal-loss and uncertain external effect tests.
5. Resume the separate deferred D26 persistent-host mission for real service restart/reboot and storage custody evidence.

Never merge a synthetic CI result into a live CP09 or autonomous-dispatch closure claim.
