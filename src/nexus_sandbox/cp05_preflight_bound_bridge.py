"""CP05 opt-in entrypoint: connector preflight must pass before checkpoint.

Provider observations and authentication flags must be supplied by a trusted
host. This module neither fetches providers nor authenticates host claims.
"""
from .cp05_connector_preflight import check_connector_pair
from .cp05_bound_checkpoint import record_bound_cortex_output
from .cortex_checkpoint_bridge import CortexCheckpointResult


def record_preflight_bound_output(coordinator, *, fixture, notion_observation,
                                  cortex_observation, expected_notion,
                                  observed_notion, notion_authenticated=False,
                                  cortex_authenticated=False,
                                  notion_complete=False, cortex_complete=False,
                                  **cortex_kwargs):
    preflight = check_connector_pair(
        fixture, notion_observation, cortex_observation,
        notion_authenticated=notion_authenticated,
        cortex_authenticated=cortex_authenticated,
        notion_complete=notion_complete,
        cortex_complete=cortex_complete,
    )
    if preflight.status != "MATCHED":
        return CortexCheckpointResult("BLOCKED", preflight.reason)
    # A passing preflight is not a checkpoint or authorization by itself.
    # Do not allow caller-supplied flags to override preflight trust results.
    for reserved in ("notion_host_authenticated", "notion_inventory_complete",
                     "host_readback_authenticated", "source_verified",
                     "authority_verified", "output_inventory_complete"):
        if reserved in cortex_kwargs:
            return CortexCheckpointResult("BLOCKED", "DUPLICATE_HOST_ASSERTIONS")
    return record_bound_cortex_output(
        coordinator, expected_notion=expected_notion,
        observed_notion=observed_notion,
        notion_host_authenticated=notion_authenticated,
        notion_inventory_complete=notion_complete,
        host_readback_authenticated=cortex_authenticated,
        source_verified=notion_authenticated and notion_complete,
        authority_verified=cortex_authenticated,
        output_inventory_complete=cortex_complete,
        **cortex_kwargs,
    )
