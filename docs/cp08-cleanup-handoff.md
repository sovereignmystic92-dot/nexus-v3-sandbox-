# CP08 cleanup handoff — bounded surviving-host implementation

The abrupt-runner supervisor now enrolls the validated owned runner/container/
staging/namespace in a cleanup journal before killing the runner or removing
those resources. The journal lives outside every removed directory in a private
`nexus-cleanup-handoff-*` directory under RUNNER_TEMP when available. Each action
commits UNCERTAIN intent before dispatch and reads it through a separate SQLite
connection. A fresh observation is required to record VERIFIED. Snapshots expose
exact run/source/target identities and expected starting states, verified actions, pending action, attempts,
event history and next permitted step. Each snapshot is also emitted to logs.
Container deletion binds to the inspected Docker ID rather than a reusable name.

An acknowledgment lost after removal leaves UNCERTAIN. Opening the same journal
never recreates missing state or repeats the removal. A later authorized caller
must bind the same plan, inspect the real target and call `reconcile`; that method
never removes anything. If the target remains, explicit ownership/scope checks
precede an explicitly requested retry. Complete repetition performs no action.
The journal and its sequence are checked against the immutable plan on reopen.
This is for one trusted worker and trusted custody, not protection against full
database replacement, privileged tampering or competing writers.

Thirteen targeted tests exercise intent-before-action, lost replies, actual process
exit after removal before acknowledgment, observation/checkpoint failures, target
still present, no-op complete repeats, wrong/missing state, corrupted completion,
ordered continuation, strict observations, failed intent commits and initialization refusal.

On failure, the supervisor retains journal/staging instead of silently running an
unjournaled deletion fallback. The next processing run must inspect the recorded
state; this patch does not install an autonomous cleanup/recovery service. A
failure before resource enrollment remains an explicit enrollment blocker, and
unknown resources must not be guessed from a partial record.

SQLite FULL plus directory fsync provides same-host local custody, not complete
host-loss protection. The host journal survives the owned runner and staging
removal; a GitHub runner can still be deprovisioned. Workflow log snapshots are
an additional observation channel, not an atomic off-host backup or proof that
every pre-action log survives host loss. Future retention deletion/provider
erasure remain outside the test. No new artifact upload, workflow trigger,
credential, remote storage, permissions, CP09 work or checkpoint-score change.

CP08's adopted owner-cp08-sandbox-2026-10-28 result remains scoped to its existing
tested sandbox boundary. This extends the resumable handoff; it does not turn
that bounded pass into original full-host/retention acceptance.
# Review hardening

Persisted PRESENT is not retry authorization. Every retry must supply a fresh
strict-Boolean `retry_scope(step)` observation bound to the saved target; absent
or rejected checks block dispatch. UNCERTAIN still requires observation-only
reconciliation first. The caller must refuse changed ownership or scope.

STOP_RUNNER records Linux boot ID, PID and `/proc` start time. Recovery must use
`original_process_absent` to compare the incarnation before considering a signal.
A changed incarnation means the original is absent: reconcile it, never signal
the replacement PID. Unreadable or malformed identity is a hold. This supplies
recovery identity, not a multi-worker lease or an automatic recovery service.
