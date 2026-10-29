# Existing checkpoint read-only reconciliation

Purpose: observe only NXS-LIVE-CHECKPOINT-40781386183 on the canonical Foundation Audit. No append, new checkpoint, deletion, permission change or bridge activation is permitted.

The original binding source is fixed to 1ff5dbffbcd900687b4477490ded37827b0cc892. The current execution source is reported separately as execution_source_revision. The earlier omitted write error cannot be recovered; this workflow can only report a fresh observation of the exact old record.

Manual workflow: Notion existing checkpoint read-only reconciliation. Run on main with checkpoint_reconcile_confirmed=true, then pass the existing notion-sandbox native gate. Defaults false, repository/main restriction, empty GitHub permissions, same checkpoint-test concurrency group. All public code comes from the exact workflow SHA. No workflow is launched by adoption.

Every execution, including attempt1, constructs the HTTP client with write_enabled=False and calls the existing probe with allow_write=False. An additional request guard refuses non-GET methods/payloads before forwarding and caps reads at11. Output retains current safe diagnostics. An exact old event yields VERIFIED_ALREADY_PRESENT; bounded absence remains BLOCKED_OBSERVE_ONLY_ABSENT; malformed or unavailable observations remain unknown/blocked. No outcome permits an append retry.

Nine mocked tests cover exact binding versus wrong source, bounded absence, independent mutation guard, read cap, sanitized HTTP status, first-attempt write exclusion, confirmation and invalid execution revision. No live read/write performed in preparation. Atomic snapshot, long-term retention, worker fencing, bridge activation and original write success remain unproved. Rollback is normal reviewed revert preserving prior run evidence.

