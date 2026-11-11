"""Host-bound, no-write CP02 preflight for a synthetic Cortex module read.

The *installed host* must supply an authenticated provider client whose
identity_exact(), permissions_exact(target) and read_exact(target) reflect
the same effective provider session. A Python mock or arbitrary callback is
NOT independent proof of that installation or the server's authorization.
"""
from .gate_bound_readonly import ReadOutcome, scoped_provider_read

VIEW_PERMISSION = "module.view"


def inspect_cortex_module(*, operation, checkpoint_statuses,
                          applicable_gates, other_boundary_evidence,
                          host):
    """Require identity + target grants before one read. No writes or data output."""
    def hold(reason):
        return ReadOutcome("HELD", reason)

    if (type(operation) is not dict or
            operation.get("provider") != "CORTEX" or
            operation.get("action") != "read" or
            operation.get("synthetic") is not True or
            type(operation.get("target")) is not str or
            not operation["target"].startswith("synthetic:")):
        return hold("SYNTHETIC_CORTEX_READ_ONLY")
    if (type(applicable_gates) not in (tuple, list, set, frozenset)
            or "CP02" not in applicable_gates
            or type(other_boundary_evidence) is not dict
            or "CP02" in other_boundary_evidence):
        return hold("CP02_HOST_EVIDENCE_REQUIRED")
    if not all(callable(getattr(host, method, None)) for method in
               ("identity_exact", "permissions_exact", "read_exact")):
        return hold("AUTHENTICATED_HOST_INTERFACE_REQUIRED")
    try:
        identity = host.identity_exact()
        if (type(identity) is not dict or set(identity) !=
                {"provider", "principal", "authenticated"} or
                type(identity["provider"]) is not str or
                type(identity["principal"]) is not str or
                type(identity["authenticated"]) is not bool or
                identity["authenticated"] is not True or
                identity["provider"] != "CORTEX" or
                identity["principal"] != operation.get("principal")):
            return hold("PROVIDER_PRINCIPAL_UNVERIFIED")
        grants = host.permissions_exact(operation["target"])
    except Exception:
        return hold("PROVIDER_IDENTITY_OR_GRANTS_ERROR")
    if (type(grants) is not dict or set(grants) !=
            {"provider", "target", "principal", "permissions", "complete"} or
            type(grants["complete"]) is not bool or not grants["complete"] or
            any(grants[key] != operation.get(key) for key in
                ("provider", "target", "principal")) or
            type(grants["permissions"]) is not list or
            any(type(x) is not str for x in grants["permissions"]) or
            VIEW_PERMISSION not in grants["permissions"]):
        return hold("EFFECTIVE_MODULE_VIEW_GRANT_UNVERIFIED")

    # CP02 assertion is derived exclusively from this host interface.
    # This remains a host assertion, never independent server attestation.
    def provider_read(provider, target):
        raw = host.read_exact(target)
        if type(raw) is not dict:
            return raw
        return raw

    return scoped_provider_read(
        operation=operation, checkpoint_statuses=checkpoint_statuses,
        applicable_gates=applicable_gates,
        boundary_evidence={**other_boundary_evidence, "CP02": True},
        read_exact=provider_read)
