"""Compose CP05 connector preflight with the existing durable checkpoint guard.

The caller must supply independently authenticated provider observations.
This module performs no provider I/O and never derives host trust from fixtures.
"""
from .cp05_connector_preflight import check_connector_pair
from .cp05_bound_checkpoint import record_bound_cortex_output
from .cortex_checkpoint_bridge import CortexCheckpointResult


def record_preflight_bound_cortex_output(
    coordinator, *, fixture, notion_observation, cortex_observation,
    notion_authenticated=False, cortex_authenticated=False,
    notion_complete=False, cortex_complete=False,
    expected_notion, observed_notion, **checkpoint_kwargs,
):
    """Only delegate to durable checkpoint after connector preflight matches.

    Even MATCHED is insufficient: the bound checkpoint separately verifies
    snapshot hash/revision, persisted archive and analysis, Cortex authority
    and independently read-back output before any stage can advance.
    """
    verdict = check_connector_pair(
        fixture, notion_observation, cortex_observation,
        notion_authenticated=notion_authenticated,
        cortex_authenticated=cortex_authenticated,
        notion_complete=notion_complete,
        cortex_complete=cortex_complete,
    )
    if verdict.status != "MATCHED":
        return CortexCheckpointResult("BLOCKED", verdict.reason)
    if (checkpoint_kwargs.get("host_readback_authenticated") is not True
            or checkpoint_kwargs.get("output_inventory_complete") is not True):
        return CortexCheckpointResult("BLOCKED", "VERIFY_CORTEX_HOST_READBACK")
    return record_bound_cortex_output(
        coordinator, expected_notion=expected_notion,
        observed_notion=observed_notion,
        notion_host_authenticated=notion_authenticated,
        notion_inventory_complete=notion_complete,
        **checkpoint_kwargs,
    )
