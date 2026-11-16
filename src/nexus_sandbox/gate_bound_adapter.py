"""Fail-closed, provider-free checkpoint gate planner for Nexus.

This is an inspection/authorization *recommendation*, not an authorization
interceptor or proof of executing provider permissions. In particular an
owner approval, passed synthetic checkpoint, or host-supplied assertion
cannot by itself authorize a provider mutation.
"""
from dataclasses import dataclass

GATE_IDS = frozenset(f"CP{i:02d}" for i in range(1, 20))
STATUSES = frozenset(("PASSED", "PARTIALLY_VERIFIED", "BLOCKED",
                      "IN_PROGRESS", "NOT_TESTED", "FAILED", "REOPENED"))
IDENT = frozenset(("NOTION", "CORTEX", "GITHUB"))
WRITE_ACTIONS = frozenset(("create", "update", "delete", "permissions", "dispatch"))


@dataclass(frozen=True)
class GateDecision:
    status: str
    next_action: str
    outstanding: tuple[str, ...]
    provider_writes: int = 0
    execution_authorized: bool = False


def assess_operation(*, operation, checkpoint_statuses, applicable_gates,
                     boundary_evidence):
    """Assess a bounded operation without executing it.

    operation keys: id, principal, provider, target, action, synthetic.
    boundary_evidence maps applicable gate IDs to verified *runtime* boolean
    observations. Observations must be supplied by a trustworthy host and
    independently corroborated; this planner cannot authenticate them.
    """
    def hold(reason, gaps=()):
        return GateDecision("HOLD", reason, tuple(sorted(gaps)))

    required = {"id", "principal", "provider", "target", "action", "synthetic"}
    if type(operation) is not dict or set(operation) != required:
        return hold("INVALID_OPERATION")
    for k in required - {"synthetic"}:
        v = operation[k]
        if type(v) is not str or not v.strip() or len(v) > 256:
            return hold("INVALID_OPERATION")
    if type(operation["synthetic"]) is not bool:
        return hold("INVALID_OPERATION")
    if operation["provider"] not in IDENT:
        return hold("UNRECOGNIZED_PROVIDER")
    if operation["action"] not in {"read"} | WRITE_ACTIONS:
        return hold("UNRECOGNIZED_ACTION")
    if (type(checkpoint_statuses) is not dict or
            set(checkpoint_statuses) != GATE_IDS or
            any(type(v) is not str or v not in STATUSES
                for v in checkpoint_statuses.values())):
        return hold("INVALID_CHECKPOINT_REGISTER")
    if type(applicable_gates) not in (tuple, list, set, frozenset):
        return hold("INVALID_GATE_SCOPE")
    if (not applicable_gates or any(type(g) is not str or g not in GATE_IDS
                                    for g in applicable_gates)):
        return hold("INVALID_GATE_SCOPE")
    if type(boundary_evidence) is not dict:
        return hold("INVALID_BOUNDARY_EVIDENCE")
    scoped = set(applicable_gates)
    if set(boundary_evidence) - scoped:
        return hold("UNSCOPED_BOUNDARY_EVIDENCE")
    if any(type(v) is not bool for v in boundary_evidence.values()):
        return hold("INVALID_BOUNDARY_EVIDENCE")
    gaps = scoped - {g for g in scoped if boundary_evidence.get(g) is True}
    if operation["action"] in WRITE_ACTIONS:
        # No write permission can be produced by this standalone library.
        # Even complete synthetic evidence must proceed through an installed,
        # authenticated provider-specific enforcement + receipt boundary.
        if not operation["synthetic"]:
            return hold("PRODUCTION_WRITE_NOT_AUTHORIZED", gaps)
        return hold("REQUIRE_INSTALLED_PROVIDER_WRITE_GUARD", gaps)
    if gaps:
        return hold("VERIFY_RUNTIME_GATE_BOUNDARIES", gaps)
    # This is a plan for a read, not proof of access or an executed read.
    return GateDecision("READ_ONLY_ELIGIBLE",
                        "VERIFY_PROVIDER_IDENTITY_AND_EXECUTE_SCOPED_READ",
                        (), 0, False)
