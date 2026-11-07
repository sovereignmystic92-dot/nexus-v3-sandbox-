# Nexus maintenance controller — execution boundary audit (2026-11-06)

## Source readback

- `tools/resume_checkpoint_workflow.py` explicitly describes an **opt-in, read-only** entrypoint. It accepts operator-provided binding/checkpoint files and verified host assertions. It **does not schedule work or execute a stage**; its result includes `automatic_execution=false`, `provider_writes=0`, `cp09=NOT_PROVEN`.
- `tools/failure_handoff.py` normalizes offline CI reports into bounded, validated failure evidence; it does not autonomously fix a failure.
- `tools/ci_failure_evidence.py` is a read-only, injected CI log evidence bridge; it does not provision credentials or repair workflows.
- The only reviewed daily GitHub schedule is `.github/workflows/nexus-cp03-cp04-evidence.yml` (`22 2 * * *` UTC). It records a trigger receipt; it is **not a maintenance executor**.
- Latest 100 GitHub Actions runs at inspection contained **no** `event=schedule`; this bounded sample cannot rule out older runs or external ChatGPT controller schedules.

## Consequence

Automatic CI exists, but the checked source does not establish an autonomous queue consumer, checkpoint-resume executor, or provider-integrated daily maintenance pipeline. It would be inaccurate to label CI or the CP03/04 receipt workflow as full unattended maintenance.

## Minimal safe implementation target

1. Identify an existing **read-only maintenance action** with deterministic inputs and a durable output destination; do not start by granting provider writes.
2. Add a dedicated schedule/event-driven **bounded coordinator** (separate from manual-only secret-bearing security probes). It should record trigger provenance, exact source revision, work item identity, action attempted, outcome, idempotency key, and readback link.
3. Keep state transitions fail-closed: no automatic provider write, retry of uncertain write, broad network privilege, or CP09 multiworker concurrency until the applicable controls are independently verified.
4. Validate hosted schedule delivery and durable readback. Only then credit **unattended maintenance** as distinct from event-triggered CI.

This is an evidence and design record only; no schedule or execution behavior was changed, no audit checkpoint was closed, and no credential was accessed.
