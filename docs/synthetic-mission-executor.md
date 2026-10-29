# Bounded synthetic mission executor — execution and recovery gate

Status: **LOCAL FIXTURE ONLY**. This is not an autonomous research agent, external write transport or scheduled workflow.

`synthetic_mission_executor.advance_synthetic` takes a PASSIVE mission contract, existing `MissionJournal`, explicit caller-supplied trigger/dependency evidence and a private local fixture directory. It executes at most **one synthetic local receipt** per invocation.

- Missing trigger or dependency: journal HOLD decision, no fixture created.
- READY: derive a receipt name from mission, contract digest and step; create an exclusive local fixture receipt only if absent. Independent readback checks expected bytes and private ownership before the step is journaled as verified.
- Interruption after receipt write but before journal append: retry compares the existing receipt and records one verified step without recreating the synthetic effect.
- Conflicting or unsafe receipt, stale journal revision, missing journal, or ACTIVE execution: fail closed.
- All bounded steps verified: return COMPLETE without another receipt.
- The optional `after_fixture_write="INTERRUPT"` switch is only a synthetic crash injection and never an external effect.

**Crucial limits:** The receipt and verifier operate on the same host and filesystem, so this is not an independent external witness or proof of third-party outcomes. A local hash/receipt cannot authorize an API write. Trigger/dependency assertions remain caller-supplied and untrusted until future host authentication. There is no scheduler, no recursive research expansion, no live Notion/Cortex integration and no cross-host ownership. The journal records local decisions but is not deployed on the deferred persistent host.

Future work, after CI: add a separate authenticated event source, independent verification source, bounded research executor with explicit budgets and failure states, and external write safety gates. Do not interpret synthetic green tests as production or CP09 closure.
