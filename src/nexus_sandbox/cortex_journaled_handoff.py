"""Journal-backed handoff boundary; no production connector or worker lock.

A host MUST supply exclusive worker fencing and independently authenticated
readback/registry evidence. Never retry an uncertain create automatically.
"""
from dataclasses import dataclass

from nexus_sandbox.cortex_handoff_journal import HandoffJournal, Intent, JournalHold, analysis_hash
from nexus_sandbox.cortex_handoff_orchestrator import execute_handoff, HandoffUncertain
from nexus_sandbox.cortex_handoff_preflight import preflight, HandoffBlocked
from nexus_sandbox.cortex_handoff_readback import verify_readback


def execute_journaled_handoff(*, journal: HandoffJournal, intent: Intent,
                             analysis_text: str, modules: list[dict],
                             destination_confirmed: bool, registry_complete: bool,
                             authorized_write: bool, exclusive_worker: bool,
                             create_module, fetch_module):
    """Single-call host boundary; durable write intent precedes remote create.

    PREPARED may be resumed only after a fresh registry preflight. WRITE_INTENT
    must be reconciled separately by an operator; no automatic retry.
    """
    if not exclusive_worker:
        raise JournalHold("host-exclusive worker ownership not established")
    if analysis_hash(analysis_text) != intent.analysis_digest:
        raise JournalHold("analysis differs from immutable journal binding")
    state, pinned_id = journal.begin(intent)
    if state == "VERIFIED":
        if not pinned_id:
            raise JournalHold("verified state lacks pinned identity")
        module = fetch_module(pinned_id)
        receipt = verify_readback(
            module=module, expected_id=pinned_id,
            expected_owner=intent.destination_owner,
            transaction_key=intent.transaction_key,
            source_url=intent.source_url, analysis_url=intent.analysis_url,
            expected_analysis=analysis_text)
        return ("RECONCILED_VERIFIED_NO_WRITE", receipt.module_id)
    if state == "WRITE_INTENT":
        raise JournalHold("uncertain prior write: independently reconcile before retry")
    decision = preflight(
        transaction_key=intent.transaction_key, source_url=intent.source_url,
        analysis_url=intent.analysis_url, destination_confirmed=destination_confirmed,
        registry_complete=registry_complete, modules=modules,
        expected_owner=intent.destination_owner)
    if decision.matched_module:
        module = fetch_module(decision.matched_module)
        receipt = verify_readback(
            module=module, expected_id=decision.matched_module,
            expected_owner=intent.destination_owner,
            transaction_key=intent.transaction_key,
            source_url=intent.source_url, analysis_url=intent.analysis_url,
            expected_analysis=analysis_text)
        # An already-existing module is reconciled without a new write.
        return ("EXISTING_MODULE_NO_WRITE", receipt.module_id)
    if not authorized_write:
        raise HandoffBlocked("explicit write authorization required")
    journal.mark_write_intent(intent)
    # The underlying orchestrator repeats preflight and readback checks.
    result = execute_handoff(
        transaction_key=intent.transaction_key, source_url=intent.source_url,
        analysis_url=intent.analysis_url, analysis_text=analysis_text,
        expected_owner=intent.destination_owner,
        destination_confirmed=destination_confirmed,
        registry_complete=registry_complete, modules=modules,
        authorized_write=True, create_module=create_module,
        fetch_module=fetch_module)
    journal.reconcile_verified(intent, result.module_id)
    return (result.status, result.module_id)
