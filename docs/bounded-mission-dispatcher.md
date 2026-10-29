# Nexus bounded mission dispatcher — sandbox contract

Status: **NON-EXECUTING / SYNTHETIC ONLY**. Part of draft PR #76.

`src/nexus_sandbox/mission_dispatcher.py` provides a deterministic decision function for a bounded mission. A host submits a declared trigger, dependency evidence, independently verified step IDs and any blocked steps. The result is a proposed next action or a HOLD/COMPLETE. It is not a live trigger subscription, execution scheduler, research agent, or journal.

## Control flow

1. Require one explicit trigger; unobserved triggers HOLD even if steps appear complete.
2. ACTIVE requires a separate bounded authorization flag; PASSIVE can evaluate evidence without authorizing a write.
3. Verify each declared dependency, in contract order; the first missing one HOLDs.
4. Conflicting/out-of-scope verified and blocked step evidence is rejected.
5. Blocked steps HOLD. Otherwise, choose the first unverified step and return READY with the action that requires executor plus independent readback.
6. COMPLETE means caller-supplied verification for all declared steps, not proof of external effects by this function.

The contract has an explicit step bound and a deterministic SHA-256 digest. Callers must journal the digest, trigger evidence, observed source identity, decisions, executor receipts and independent readback; a mere READY decision may **never** be interpreted as authority to perform external writes.

## Next integration gates

- Persist a mission contract and evidence in an authorized durable execution journal, with crash-safe retry and revision binding. The pure decision alone has no durability.
- Authenticate and scope incoming triggers. Do not treat an event payload or an assertion flag as evidence of authorization.
- Attach a bounded executor that returns evidence, and an independent verifier that checks it before marking a step verified. Require an explicit stop condition and a finite research/step budget; do not recursively expand missions without a new bounded contract.
- Add restart/replay, loss-of-journal, conflicting event, stale source, uncertain effect, and over-budget tests.
- Only after the deferred persistent-host mission is resumed and its real gates pass should unattended PASSIVE scheduling be considered. Notion checkpoint projection and Cortex live write callbacks remain disabled.

This file does not lift deferrals, activate Cortex, enable a cron trigger, merge the PR or close CP09.
