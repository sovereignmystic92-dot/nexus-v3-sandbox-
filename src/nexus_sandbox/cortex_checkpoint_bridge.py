"""Read-only Cortex output checkpoint bridge.

The trusted host must independently authenticate provider readback and custody.
This module makes no provider calls or writes, and does not assert CP09.
"""
from dataclasses import dataclass

from .cortex_pilot_receipt import verify_cortex_pilot
from .transcript_ingestion import TranscriptCoordinator


@dataclass(frozen=True)
class CortexCheckpointResult:
    status: str
    next_action: str
    source_key: str | None = None
    provider_writes: int = 0
    automatic_execution: bool = False
    cp09: str = "NOT_PROVEN"


def record_verified_cortex_output(
    coordinator: TranscriptCoordinator, *, source_key: str,
    route: dict, expected_output: dict, observed_output: dict,
    readback_ref: str, host_readback_authenticated: bool = False,
    source_verified: bool = False, authority_verified: bool = False,
    output_inventory_complete: bool = False,
) -> CortexCheckpointResult:
    """Advance only after an existing analysis checkpoint and exact Cortex readback.

    All host flags are assertions, not cryptographic proof. The host owns
    authentication, authorization, pagination, revision custody and readback.
    """
    def hold(action):
        return CortexCheckpointResult("BLOCKED", action)
    if any(type(flag) is not bool for flag in
           (host_readback_authenticated, source_verified,
            authority_verified, output_inventory_complete)):
        return hold("VERIFY_HOST_ASSERTIONS")
    if not host_readback_authenticated:
        return hold("AUTHENTICATE_CORTEX_READBACK")
    if type(readback_ref) is not str or not readback_ref:
        return hold("REQUIRE_CORTEX_READBACK_REFERENCE")
    if type(route) is not dict:
        return hold("FIX_ROUTE_SCHEMA")
    archive = coordinator.get(source_key, "NOTION_ARCHIVE_VERIFIED")
    analysis = coordinator.get(source_key, "ANALYSIS_COMPLETED")
    if archive is None or archive.status != "COMPLETE" or not archive.verified:
        return hold("VERIFY_NOTION_ARCHIVE_CHECKPOINT")
    if analysis is None or analysis.status != "COMPLETE" or not analysis.verified:
        return hold("VERIFY_PERSISTED_ANALYSIS_CHECKPOINT")
    if (route.get("source_id") != archive.evidence.get("destination", "").removeprefix("notion:")
            or route.get("source_revision") != archive.evidence.get("source_revision")
            or route.get("source_sha256") != archive.evidence.get("raw_sha256")):
        return hold("RECONCILE_ARCHIVE_ROUTE_BINDING")
    receipt = verify_cortex_pilot(
        route, expected_output, observed_output,
        source_verified=source_verified, authority_verified=authority_verified,
        output_inventory_complete=output_inventory_complete)
    if receipt.status != "READBACK_MATCHED":
        return hold(receipt.next_action)
    evidence = {"destination": "cortex:" + route["output_id"],
                "readback": readback_ref,
                "output_revision": route["output_revision"],
                "output_sha256": receipt.output_sha256,
                "source_sha256": route["source_sha256"]}
    coordinator.record(source_key, "CORTEX_OUTPUT_VERIFIED", "COMPLETE",
                       evidence, independently_read_back=True)
    return CortexCheckpointResult("RECORDED", "VERIFY_FINAL_RECEIPT", source_key)
