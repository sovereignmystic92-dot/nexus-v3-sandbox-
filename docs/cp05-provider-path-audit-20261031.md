# CP05 provider-path enforcement audit — 2026-10-31

Status: READ-ONLY OBSERVATIONS; NOT CP05 PASS. No provider mutation performed in this audit.

## Surfaces
1. GitHub isolated synthetic acceptance: hosted run 41251932912 passed at PR #119 test revision; four CP05 synthetic binding tests passed. This tests local SQLite synthetic guard, not direct provider enforcement.
2. Repository `src/nexus_sandbox/cortex_adapter.py`: module docstring explicitly declares single-worker synthetic Cortex persistence, no network/credentials, host-supplied transport, non-atomic sequential reads and uncertain-write reconciliation. Thus guard is not automatically a host-wide enforcement layer.
3. Notion connector: `notion_get_self` returned a connected workspace and authenticated person ID. This proves a connected identity is reported, not effective permissions, a restricted synthetic-only identity, or write-path mediation. Tool access lookup confirmed `fetch` available but did not return a complete permission inventory.
4. Socra Cortex connector: `module_list` returned existing disposable CP05 probe module `module_01m69vmnfqx2jhsm5rn5kxf3mj` at version 2 with both original and update markers. `context_access` reported owner and module.view/edit/admin, issue.view/create/comment/edit/admin, module.delete/transfer. This is a broad reported permission set, not a demonstrated restricted synthetic-only identity. No negative provider access attempt performed.
5. Direct provider tools are callable separately from the GitHub sandbox runner. No observed host-side proof that every such tool invocation passes through the repository's allowlist and preflight. Treat as an enforcement gap, not a proven vulnerability or successful bypass.

## Decision
CP05 remains PARTIALLY_VERIFIED. CP02 effective-grants restriction remains BLOCKED. Do not interpret connector-reported permissions as a limited synthetic account. No safe negative write or denial test can establish a zero-mutation guarantee without an explicitly isolated provider test identity and approved disposable targets.

## Next acceptance evidence
- Complete effective-grants inventory for each execution identity and route.
- Documented mapping from each provider operation to Nexus guard/preflight or an explicit prohibited/out-of-scope route.
- Restricted disposable identity and provider-owned synthetic allowlist, with positive and denied-target tests, independently read back.
- Guarded provider create/update, version conflict, uncertain-write reconciliation, and independent reviewer signoff.
- No gate promotion, live activation or PR merge based solely on this audit.
