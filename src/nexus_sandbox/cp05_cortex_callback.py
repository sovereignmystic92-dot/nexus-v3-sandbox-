"""Read-only CP05 bridge to the existing operator-authenticated Cortex callback.

The callback's module data is an observation, never proof of host identity,
credential provenance, effective grants, or checkpoint durability.
"""
from .cortex_tools import CortexToolTransport


def observe_cortex_module(*, module_id, exact_name, invoke):
    """Return (record, unattested_metadata) for an exact synthetic module.

    The operator supplies an already authenticated tool callback. This
    function neither authenticates it nor grants CP05 host attestation.
    """
    if (not isinstance(module_id, str) or not module_id.startswith("module_")
            or not isinstance(exact_name, str) or not exact_name
            or not callable(invoke)):
        raise ValueError("Exact Cortex fixture and callback required")
    module = CortexToolTransport(invoke).get(exact_name)
    if module is None:
        raise ValueError("Cortex module absent")
    if module.id != module_id:
        raise ValueError("Cortex module identity mismatch")
    return ({
        "module_id": module.id,
        "name": module.name,
        "version": module.version,
        "content": module.content,
        "dependencies": list(module.dependencies),
    }, {
        "authenticated": False,
        "complete_inventory": False,
    })
