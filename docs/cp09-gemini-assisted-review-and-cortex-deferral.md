# CP09 Gemini-assisted fencing review and Cortex deferral

2026-11-08 UTC. Owner decision: defer live Cortex OAuth/installation/write/readback work pending a suitable machine or verified accessible provider capability. This is an environmental dependency, not a passed CP02/CP05 gate. Preserve completed Notion/Gemini/GitHub evidence. **Do not repeat blocked credential attempts or enable provider writes.**

## CP09 observed counterexample

[Historical C9 report](c9/ownership-and-fencing.md) reproduced stale-worker overwrite with separate and shared journals. Delayed A mutated target after B verified a newer state; readback only detected the damage after mutation. A same-key shared-journal test blocked one duplicate schedule but does not establish remote fencing.

## What live Gemini can do

- Independently inspect the exact source and synthetic probe at a pinned SHA.
- Produce a structured review of competing-worker interleavings, stale/in-flight writes, takeover, journal loss, direct-caller bypass and uncertain acknowledgments.
- Review proposed gateway/conditional-write designs and test harness changes. GitHub Actions can execute offline tests; Gemini feedback is advisory until source-bound, reproducible and reviewed.
- No Gemini output can confer remote CAS, effective exclusive grants or prevent direct callers at the Cortex mutation boundary.

## Acceptance matrix (must fail closed)

| Scenario | Required assertion |
|---|---|
| Simultaneous ownership | Only one generation can commit |
| Takeover | Old generation rejected by actual mutation service |
| Delayed old request | No stale mutation after takeover |
| Previously accepted in-flight request | Must finish before takeover or be rejected atomically |
| Gateway restart | Durable ownership and old-token rejection |
| Unknown acknowledgment | Reconcile, never blind retry |
| Direct caller bypass | Cannot mutate outside enforced exclusive authority |

## Operating policy

Until backend CAS/fencing or a genuinely exclusive, quiescence-proven single-writer gateway is independently demonstrated: **one designated writer, no automatic ownership transfer, no live multiworker testing**. Gemini and ChatGPT/Codex may analyze/test in parallel but must not concurrently mutate shared Cortex fixtures. No production or CP09 closure.

## Evidence and next actions

1. Re-run existing synthetic CP09 counterexample at a pinned commit; record original failure as an expected unsafe outcome, not a pass for fencing.
2. Build a separate fail-closed synthetic conditional-write gateway model and tests for the matrix above; distinguish model guarantees from real provider guarantees.
3. Feed source-bound test outcomes to live Gemini review only through an approved read-only workflow with bounded inputs, costs and redacted outputs. Do not silently reuse transcript-specific authorization for new CP09 data.
4. Record reviewer ID/model/response digest, tested SHA, test run IDs and unresolved gaps.
5. Resume Cortex live acceptance only when actual provider identity, effective grants and remote mutation enforcement are verifiable.

## Other audit work

Continue CP01–CP04, CP06–CP08, CP10–CP19 evidence reconciliation independently of deferred Cortex provider work. CP02 and CP05 remain OPEN; CP09 remains BLOCKED for multiworker.
