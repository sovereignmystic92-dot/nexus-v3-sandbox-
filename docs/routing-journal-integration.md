# Nexus routing decision ↔ mission journal (sandbox only)

Status: **IMPLEMENTED AS NON-EXECUTING CODE; TEST RESULTS NOT YET VERIFIED.**

The new `routing_journal` module writes a routing proposal against an existing `MissionJournal` revision. A proposal includes the contract digest, local entry hash, proposed lead and distinct reviewer, deterministic routing digest, and an explicit `NON_EXECUTING_PROPOSAL` authority. It does not send work to an agent or authorize external effects.

## Process

1. Explicitly provision the existing private SQLite journal and its routing table.
2. Record a mission's trigger/dependency evidence through `MissionJournal.record`.
3. Call `record_routing_proposal` with the exact existing mission revision, required skills, and agent roster.
4. Reopen the same journal and use `observe_routing_proposal` to read back the assignment.
5. Identical replays return the same entry. A changed roster or other conflicting proposal at the same revision is rejected. A new proposal after revised evidence requires the new committed mission revision.

## Covered by committed tests (not CI-verified)

`tests/unit/test_routing_journal.py` tests identical replay, separate lead/reviewer, reopening, conflicting roster, missing reviewer approval, missing trigger, stale revision, missing journal, missing routing schema, and evidence revision progression.

## Remaining limitations

- This is *proposal* persistence only; there is no execution handoff, remote receipt or independent reviewer verdict journaling yet.
- The roster/trigger assertions supplied by the caller are not authenticated. A matching digest is not external proof.
- Routing table entries are pinned to the mission-journal entry hash but do **not** have their own cryptographic append-only chain or external readback.
- A single local SQLite file is not evidence of persistence across independent GitHub Actions runner hosts or distributed fencing.
- Cross-process, CI and restart tests must be run and examined before treating the gate as validated. No CI run was returned at commit `bf418d3` when checked.
- D26 host provisioning remains deferred. No production execution, Notion/Cortex writes, schedules, audit closure or merge.

## Next checkpoint

Run the nine committed routing-journal tests in a trusted CI runner; fix failures. Then add bounded lead-result/reviewer-verdict records with authenticated provenance, replay protection and restart tests. Only after those pass should operator-authorized collaboration be expanded.
