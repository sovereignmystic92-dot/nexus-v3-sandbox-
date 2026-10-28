# CP08/CP09 synthetic mutation-boundary reference — draft

The existing C9 probe demonstrates that a shared client journal cannot reject a
stale writer at an external mutation boundary. This proposal provides a small
SQLite reference target in which ownership generation, stopped state and payload
are serialized in the *same* transaction. It is not wired into any provider,
adapter, pipeline, gateway or workflow. Review is required before integration.

Two processes racing to acquire an unowned target yield one owner. An explicit
trusted takeover advances a persisted generation. Old owner tokens cannot mutate
or stop the new owner's target. A stop tombstone revokes further writes and
acquisition while preserving payload evidence. Opening missing state fails rather
than silently resetting ownership. Local fixture cleanup removes only test-owned
temporary directories after connections/processes are closed.

This reference is deliberately not a lease service: no clock expiry, credentials,
identity authentication, remote storage, automatic takeover or external writes.
The generation is not a secret, and a caller who can bypass the API or modify the
SQLite database is outside this boundary. SQLite transaction ordering supplies
the guarantee; a remote adapter must not copy the preflight check and then perform
an unconditional provider write. That would reintroduce the original race.

## Validation and limits

Twelve targeted tests passed locally with an empty inherited environment plus
explicit PATH/PYTHONPATH/PYTHONDONTWRITEBYTECODE. Docker is unavailable here;
this local result is not hosted isolated acceptance evidence.

Targeted tests cover two-process acquisition, a delayed stale process after
takeover, reopening persisted ownership, wrong targets, stop/reacquire rejection,
missing-state refusal and test-owned temporary cleanup. These are real local
SQLite operations using synthetic text, not remote-provider conformance tests.
The delayed-process case waits before entering the target transaction; it does
not simulate an already accepted remote request or establish safe remote failover.
No power-loss, host-loss, retention-expiry or provider-replica deletion claim.

CP08 already has PR #42 for abrupt runner loss with a surviving supervisor. Do not
duplicate it or confuse this local stop barrier with supervisor cleanup. Its
historical [run 40160521612](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/40160521612),
attempt 1/job 121070915442, was independently decoded: head
`67d608fab3bcb44ee100d05363e940373ef0b417` was represented by tested merge candidate
`86d96ad470759d095d2cbd3945151927d34bb008` against base
`0c32f1c2a746fe1e50a01b9fde378d2b6759ce9a`. It reports 216 tests and a passing
REAL-DOCKER-RUNNER-SIGKILL-SUPERVISOR case with observed orphan/staging cleanup.
Current-main integration still needs validation. CP08 stays partial.

CP09 remains blocked for Notion/Cortex multiworker writes. Before adoption at a
real mutation boundary, demonstrate service-enforced conditional writes and
generation checks, or an exclusive gateway whose downstream requests cannot
outlive authority. Prove simultaneous acquisition, stale request rejection,
accepted in-flight request handling, restart/takeover and direct-caller bypass
controls against the actual service. Do not change permissions to obtain that
proof under this draft. The existing single-worker restriction remains.

No gate definition, checkpoint count, workflow/security setting, credential,
production service or automatic listener is changed. This is a draft review
artifact under the owner's authorization to work on CP08 and CP09.
