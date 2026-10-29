# Verified Notion readback -> read-only resume plan

Current manual entrypoint: **Notion saved checkpoint resume plan (read-only)**, file notion-checkpoint-reconcile-probe.yml. Run on main with checkpoint_reconcile_confirmed=true and the existing Notion-sandbox native gate. Adoption never dispatches the workflow. The original reconciliation script remains available as historical code; old runs preserve their exact original source and target.

## Fixed checkpoint and observation
The current handoff targets successful run40862662915 on canonical Foundation Audit4018c067daa48122b82ec2ae8067d021. Its binding source is d55ecbe22b9a34ab0c9498cc5f7014aac20e77b2 and checkpoint digest is7409a0f2aae701d8d1c4cbce51426d96f455ec989f8e966ea3243696bdca17a8. Execution source is reported separately.

The adopted NotionCheckpointAPI and AuditCheckpointTransport perform bounded exact-page/table inventory and checkpoint-chain observation. An independent expected binding and digest must match before the adopted decoder/classifier is invoked. Root/table reads share the existing limits; wrapper caps11GETs. No checkpoint text or provider messages are printed, only fixed stages, binding metadata and sanitized diagnostics. Missing, malformed, incomplete or changed observations block rather than becoming a resume plan.

## Two separate judgments
A successful observation returns VERIFIED_OBSERVATION_EXECUTION_BLOCKED. It emits observed completed/pending/next stage fields, then passes the exact verified checkpoint to decide_resume with inventory_complete=True because the adapter/transport observation completed.

Execution authority remains hardcoded False, not a user flag. The resume decision is BLOCKED / VERIFY_CURRENT_AUTHORITY. The current enrollment has zero receipts, so observed_next_stage is SOURCE_PRESERVED; it is not permission to invoke that stage. Exit0 means observation and decision output succeeded, never that execution is authorized or processing is complete.

Every attempt constructs write_enabled=False, provides no append capability, rejects non-GET/payload requests before the callback, and has no executor wiring. provider_writes=0, executor_callbacks_invoked=0 and automatic_execution=False describe the actual connected path; callback/provider internals still require trusted host custody. Complete effective grants, current worker authority and ownership/fencing are not authenticated by a successful GET.

## Validation and history
Nine new synthetic tests cover actual classifier handoff, missing authority, absent/misbound/digest-mismatched/incomplete records, defense-in-depth mutation exclusion, read budget, HTTP diagnostic sanitization and first-attempt write-disabled configuration. No live provider call was performed during preparation. Actual provider execution must be checked from its later run logs.

The historical PR80 workflow targeted failed run40781386183; its absence results did not test the later successful record. The successful record was independently observed across attempts of run40862662915 without a second append. Neither that result nor this handoff proves host-loss recovery, future retention, live job completion or CP09 fencing.

No live processing, append, new enrollment, permissions, credentials, scheduler or broad bridge activation. Production remains paused; CP09 unproven; no checkpoint score promotion. Rollback is normal reviewed revert preserving prior run evidence.

