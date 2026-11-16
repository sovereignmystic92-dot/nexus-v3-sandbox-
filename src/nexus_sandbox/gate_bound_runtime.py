"""Compose the Cortex API GET transport with Nexus's CP02 gate boundary.

Deployment MUST provision a distinct scoped Socra OAuth token and an actual
authenticated identity verifier from the same host session. Nothing here
extracts ChatGPT app tokens, installs a workflow or authorizes a provider write.
"""
from .gate_bound_connector import CortexConnectorReadHost
from .gate_bound_host import inspect_cortex_module
from .gate_bound_https import CortexReadOnlyHTTPS


def inspect_with_cortex_oauth(*, token, authenticated_identity_exact,
                              module_name, module_id, operation,
                              checkpoint_statuses, applicable_gates,
                              other_boundary_evidence, opener=None):
    """Execute GET /access then GET /module behind the CP02 read-only guard.

    The identity callback's provenance cannot be verified by this library.
    Caller must not supply an invented principal/constant or repurpose an
    owner's token for a restricted-viewer negative test.
    """
    if (type(module_name) is not str or not module_name.startswith("Nexus Sandbox ")
            or type(module_id) is not str or not module_id.startswith("module_")
            or type(operation) is not dict or
            type(operation.get("target")) is not str or
            not operation["target"].startswith("synthetic:")):
        raise ValueError("Exact pinned synthetic resource binding required")
    transport = CortexReadOnlyHTTPS(token, opener=opener)
    host = CortexConnectorReadHost(
        invoke=transport,
        identity_exact=authenticated_identity_exact,
        module_names={operation["target"]: (module_name, module_id)})
    return inspect_cortex_module(
        operation=operation, checkpoint_statuses=checkpoint_statuses,
        applicable_gates=applicable_gates,
        other_boundary_evidence=other_boundary_evidence, host=host)
