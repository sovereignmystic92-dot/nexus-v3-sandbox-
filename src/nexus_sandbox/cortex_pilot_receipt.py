"""Pilot-only verified Cortex output receipt contract.

This is NOT an authenticated provider adapter. Caller must independently
retrieve complete Notion source and saved Cortex output using current grants.
No writes, execution, dispatch or five-pass promotion happen here.
"""
import hashlib
import json
from dataclasses import dataclass

from .output_authority import validate_output_route


@dataclass(frozen=True)
class PilotReceipt:
    status: str
    next_action: str
    output_sha256: str | None = None
    provider_writes: int = 0
    automatic_execution: bool = False
    cp09: str = "NOT_PROVEN"


def verify_cortex_pilot(route, expected_output, observed_output, *,
                        source_verified=False, authority_verified=False,
                        output_inventory_complete=False):
    """Strictly compare frozen intended output with independently read-back bytes.

    Inputs are trusted-host observations, NOT evidence of authenticity by
    themselves. Incomplete or mismatching readback must hold without retry.
    """
    def blocked(next_action):
        return PilotReceipt("BLOCKED", next_action)

    if any(type(x) is not bool for x in (
            source_verified, authority_verified, output_inventory_complete)):
        return blocked("VERIFY_HOST_ASSERTIONS")
    verdict = validate_output_route(route,
        archive_readback_verified=source_verified,
        cortex_authority_verified=authority_verified,
        cortex_output_readback_verified=False)
    if verdict.status != "ROUTED_NOT_COMPLETE":
        return blocked(verdict.next_action)
    if not output_inventory_complete:
        return blocked("FETCH_COMPLETE_CORTEX_OUTPUT")
    if type(expected_output) is not dict or type(observed_output) is not dict:
        return blocked("INVALID_OUTPUT_SNAPSHOT")
    required = {"output_id", "source_id", "source_sha256",
                "revision", "analysis"}
    if set(expected_output) != required or set(observed_output) != required:
        return blocked("INVALID_OUTPUT_SNAPSHOT")
    if any(type(v) is not str or not v for v in expected_output.values()):
        return blocked("INVALID_OUTPUT_SNAPSHOT")
    if any(type(v) is not str or not v for v in observed_output.values()):
        return blocked("INVALID_OUTPUT_SNAPSHOT")
    if (expected_output["output_id"] != route["output_id"] or
            expected_output["revision"] != route["output_revision"] or
            expected_output["source_id"] != route["source_id"] or
            expected_output["source_sha256"] != route["source_sha256"]):
        return blocked("RECONCILE_OUTPUT_BINDING")
    frozen = json.dumps(expected_output, sort_keys=True, ensure_ascii=False,
                        separators=(",", ":")).encode("utf-8")
    observed = json.dumps(observed_output, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":")).encode("utf-8")
    if observed != frozen:
        return blocked("RECONCILE_UNCERTAIN_CORTEX_WRITE_NO_RETRY")
    return PilotReceipt("READBACK_MATCHED",
                        "REVIEW_REMAINING_NEXUS_COMPLETION_GATES",
                        hashlib.sha256(observed).hexdigest())
