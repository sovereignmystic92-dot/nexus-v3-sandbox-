# CP05 deferral and CP08 follow-through

Owner decision: defer authenticated caller/account and effective-permission verification, finish other feasible sandbox work and proceed to the next gate. Deferral does not pass CP05 or authorize production/unattended writes.

## Fixture routing

Malformed structured responses, malformed text blocks and unhashable destination arguments now raise a controlled ToolFailure before mutation. Two new regression methods exercise malformed service responses and invalid destinations, requiring only the expected preflight read or zero provider calls. An empty/false structured response is no longer silently replaced by a text fallback. Pinned identity/root guards and disabled unenrolled creation remain.

CP05 remains partial. Creation/enrollment is intentionally disabled; adding safe enrollment is a separate implementation task, not complete. Guarded live-update validation and full host routing assurance remain open. No live provider write or authentication probe was performed. Direct connector callers remain outside the Python library guard. It would be inaccurate to claim all nonidentity requirements are complete.

## Next gate: CP08 cleanup

Source-staging cleanup exceptions previously escaped the runner's final reporting path. cleanup_staging now preserves a redacted structured failure, marks the run BLOCKED and confirms filesystem absence before claiming removal. A retry can establish removal without rewriting the failed run as successful. Two regressions cover deletion failure with retained evidence and a no-op cleanup followed by retry.

Local validation: 214 distinct tests passed. After restoring the original root-identity assertion to its original test, all six runner-boundary/cleanup tests passed again. Hosted validation is pending at initial publication. No workflow changes, no host shutdown, no deletion of retained user/provider artifacts and no retention-setting changes.

CP08 remains partial: this tests application cleanup failure handling, not forced host loss or future service deletion. Accepted gate count stays 11/19. The current changes must be reviewed in GitHub before adoption; no requirement/denominator change or new pass is proposed.
