# Automated processing sequence — draft orchestration

Owner request: close the recurring gap between explaining input and finishing the
saved Nexus output across all qualifying processing tasks and ChatGPT threads.

The runner automatically advances through source preservation, context loading,
duplicate assessment, analysis, persistence, registration and final readback.
Every executor must return a run/stage-bound verified receipt with evidence refs.
Each successful stage also requires save_checkpoint followed by a separate
read_checkpoint matching the complete ordered receipt sequence. Missing/misbound
evidence, exceptions and checkpoint mismatch stop the run before COMPLETE.
An ANALYZED receipt never suffices to report a complete transaction.

Eight orchestration tests plus the existing 27 focused tests passed locally:
35 total. Tests cover automatic continuation, unsaved-output hold, run/stage
mismatch, strict boolean evidence, checkpoint failure, missing executor and
final-readback failure. These tests use fake executors and in-memory checkpoint
callbacks; they do not establish persistent runtime custody.

This is orchestration scaffolding, not a deployed chat trigger. The host must
supply authorized actual source, processing, persistence, duplicate-lookup,
registration and readback executors. Evidence references are contract inputs,
not proof that arbitrary callbacks told the truth. No provider write methods,
credentials, automatic retries, restart replay or new live approval are added.
No callback execution is implied by importing the module.

Stage failures return their exact unresolved stage; an executor may have mutated
before failing, so callers must reconcile rather than replay blindly. Process
death or complete checkpoint loss still needs the separately reviewed durable
journal/restore design. Automatic source arrival detection and mandatory ChatGPT
invocation remain unimplemented. Existing runtime/storage deferrals stand.

Operational instructions in Cortex Agent Operating Instructions, Chat ↔ Nexus
Execution Contract and Nexus Initialization Protocol now explicitly require
save/verify before completion reports and continuing authorized executable work
after interim updates. Saved instructions plus this draft code do not prove
automatic enforcement in fresh chats. No production, merge or gate promotion.
