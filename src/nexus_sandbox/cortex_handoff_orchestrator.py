"""Fail-closed orchestration boundary for Notion-derived Cortex outputs.

Injected host callbacks must implement real authenticated connector operations.
This module does not itself supply credentials, triggers, locks, or production
authorization; a host must supply those and durable operation reconciliation.
"""
from dataclasses import dataclass
from typing import Callable

from nexus_sandbox.cortex_handoff_preflight import preflight, HandoffBlocked
from nexus_sandbox.cortex_handoff_readback import verify_readback, ReadbackFailure


class HandoffUncertain(RuntimeError):
    """Write may have happened; never blindly retry."""


@dataclass(frozen=True)
class HandoffResult:
    status: str
    module_id: str
    version: int | None


def execute_handoff(*, transaction_key: str, source_url: str,
                    analysis_url: str, analysis_text: str,
                    expected_owner: str, destination_confirmed: bool,
                    registry_complete: bool, modules: list[dict],
                    authorized_write: bool,
                    create_module: Callable[[str, str], dict],
                    fetch_module: Callable[[str], dict]) -> HandoffResult:
    """Only a separately authorized host may enable a create.

    The host must establish exclusive execution, stable idempotency and
    durable outcome logging; this function alone is not a live adapter.
    """
    if not isinstance(analysis_text, str) or not analysis_text.strip():
        raise HandoffBlocked("missing derived analysis")
    decision = preflight(
        transaction_key=transaction_key, source_url=source_url,
        analysis_url=analysis_url, destination_confirmed=destination_confirmed,
        registry_complete=registry_complete, modules=modules,
        expected_owner=expected_owner)
    if decision.matched_module:
        # Reconcile, never create a duplicate.
        module_id = decision.matched_module
        try:
            module = fetch_module(module_id)
            receipt = verify_readback(
                module=module, expected_id=module_id,
                expected_owner=expected_owner, transaction_key=transaction_key,
                source_url=source_url, analysis_url=analysis_url,
                expected_analysis=analysis_text)
        except Exception as exc:
            raise HandoffUncertain("existing module reconciliation failed") from exc
        return HandoffResult("RECONCILED_EXISTING_NO_WRITE", module_id, receipt.version)
    if not authorized_write:
        raise HandoffBlocked("explicit host write authorization required")
    name = "Nexus Derived Output — " + transaction_key
    content = ("Transaction: " + transaction_key + "\\n"
               + "Canonical source: " + source_url + "\\n"
               + "Canonical analysis: " + analysis_url + "\\n"
               + "Derived analysis:\\n" + analysis_text)
    try:
        created = create_module(name, content)
    except Exception as exc:
        raise HandoffUncertain("create outcome uncertain; reconcile before retry") from exc
    if not isinstance(created, dict) or not created.get("id"):
        raise HandoffUncertain("create receipt missing module ID; reconcile before retry")
    module_id = created["id"]
    try:
        module = fetch_module(module_id)
        receipt = verify_readback(
            module=module, expected_id=module_id, expected_owner=expected_owner,
            transaction_key=transaction_key, source_url=source_url,
            analysis_url=analysis_url, expected_analysis=analysis_text)
    except Exception as exc:
        raise HandoffUncertain("create may have succeeded but readback failed; reconcile") from exc
    return HandoffResult("CREATED_AND_READBACK_VERIFIED_NOT_LIVE_ACCEPTANCE",
                         module_id, receipt.version)
