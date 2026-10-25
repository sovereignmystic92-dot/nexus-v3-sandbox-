# CP08 disposable provider deletion result

Owner gave standing approval for ongoing nonbilling Nexus sandbox audit work. This does not enable billing, incur charges or activate production. Record is scoped to the ongoing audit, not arbitrary unrelated actions.

## Observed sequence

1. Exact unique synthetic probe name read returned the observed missing-module error.
2. One new marked synthetic module was created with no parent/dependencies, version 1.
3. A separate context_get matched exact name, returned identity, full content, version, unarchived state and empty dependency list.
4. context_delete returned INVALID_ARGUMENT: modules are durable knowledge and cannot be deleted; service recommends archiving.
5. Another context_get confirmed the exact content remains present and archived=false. No archive, retry, repair or existing record mutation was attempted.

Only target created: `Nexus Sandbox CP08 Disposable Deletion Probe 20261025-0400-66ae5e19`. Public record excludes provider account and module IDs. Existing audit fixtures and production records were unchanged. This new disposable module remains present because the provider refused deletion.

## Verdict

Creation and immediate persistence readback: VERIFIED. Deletion operation: REJECTED_BY_PROVIDER. Absence: NOT ESTABLISHED; continued existence observed. Immediate provider deletion is not supported by this observed Cortex path. No archive-as-delete substitution, automatic expiry or backend erasure claim.

GitHub connector artifact tools expose list/download but no upload/delete operation. No existing Actions artifacts or logs were deleted. Cortex result does not establish GitHub retention policy. CP08 remains PARTIALLY_VERIFIED; count stays 11/19. Next provider decision is an actual deletion-capable disposable store or an explicit retained-versus-deleted data policy; neither would retroactively establish Cortex hard deletion or host-loss cleanup.
