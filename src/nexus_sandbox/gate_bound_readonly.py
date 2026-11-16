"""Read-only checkpoint-bound provider-call wrapper for a trusted Nexus host.

No credentials, connector implementation, network stack, or write capability
are included. A supplied read function must be provided by an authenticated
host. This wrapper cannot prove host identity or effective provider grants.
"""
from dataclasses import dataclass
from .gate_bound_adapter import assess_operation


@dataclass(frozen=True)
class ReadOutcome:
    status: str
    next_action: str
    outstanding: tuple[str, ...] = ()
    resource_revision: str | None = None
    provider_writes: int = 0
    execution_authorized: bool = False


def scoped_provider_read(*, operation, checkpoint_statuses, applicable_gates,
                         boundary_evidence, read_exact):
    """Run a single narrowly scoped read after non-authorizing gate planning.

    The read_exact callback must take (provider, target) and return an exact
    snapshot with keys: provider, target, principal, revision, complete,
    truncated. Data and secrets are never returned in the summary.
    """
    verdict = assess_operation(
        operation=operation, checkpoint_statuses=checkpoint_statuses,
        applicable_gates=applicable_gates, boundary_evidence=boundary_evidence)
    if verdict.status != "READ_ONLY_ELIGIBLE":
        return ReadOutcome("HELD", verdict.next_action, verdict.outstanding)
    if type(operation) is not dict or operation.get("action") != "read":
        return ReadOutcome("HELD", "READ_ONLY_OPERATION_REQUIRED")
    if not callable(read_exact):
        return ReadOutcome("HELD", "AUTHENTICATED_READ_CALLBACK_REQUIRED")
    try:
        snapshot = read_exact(operation["provider"], operation["target"])
    except Exception:
        return ReadOutcome("HELD", "PROVIDER_READ_FAILED")
    required = {"provider", "target", "principal", "revision", "complete",
                "truncated"}
    if type(snapshot) is not dict or set(snapshot) != required:
        return ReadOutcome("HELD", "INVALID_PROVIDER_READBACK")
    if (any(type(snapshot[k]) is not str or not snapshot[k] or
            len(snapshot[k]) > 256
            for k in ("provider", "target", "principal", "revision"))
            or type(snapshot["complete"]) is not bool
            or type(snapshot["truncated"]) is not bool):
        return ReadOutcome("HELD", "INVALID_PROVIDER_READBACK")
    if (any(snapshot[k] != operation[k] for k in
            ("provider", "target", "principal"))
            or not snapshot["complete"] or snapshot["truncated"]):
        return ReadOutcome("HELD", "MISMATCHED_OR_INCOMPLETE_READBACK")
    return ReadOutcome("READBACK_MATCHED_HOST_ASSERTION",
                       "INDEPENDENTLY_VERIFY_PROVIDER_PRINCIPAL_AND_REVISION",
                       resource_revision=snapshot["revision"])
