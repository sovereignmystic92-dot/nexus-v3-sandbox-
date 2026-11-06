"""Host-bound, journaled Cortex handoff composition.

All evidence must be independently acquired by the host. This is NOT a
production authentication or distributed-fencing implementation.
"""
from nexus_sandbox.cortex_host_binding import validate_host_binding, HostBindingBlocked
from nexus_sandbox.cortex_handoff_journal import Intent, JournalHold
from nexus_sandbox.cortex_journaled_handoff import execute_journaled_handoff


def execute_host_bound_handoff(*, journal, intent: Intent, analysis_text,
                               source_page_id, analysis_page_id,
                               observed_account, observed_owner,
                               registry_pages, registry_complete,
                               source_verified, analysis_verified,
                               exclusive_worker, durable_journal,
                               modules, authorized_write,
                               create_module, fetch_module):
    binding = validate_host_binding(
        transaction_key=intent.transaction_key,
        source_page_id=source_page_id,
        analysis_page_id=analysis_page_id,
        source_revision=intent.source_revision,
        analysis_revision=intent.analysis_revision,
        destination_account=intent.destination_account,
        destination_owner=intent.destination_owner,
        observed_account=observed_account,
        observed_owner=observed_owner,
        registry_pages=registry_pages,
        registry_complete=registry_complete,
        source_verified=source_verified,
        analysis_verified=analysis_verified,
        exclusive_worker=exclusive_worker,
        durable_journal=durable_journal)
    if binding.transaction_key != intent.transaction_key:
        raise JournalHold("host binding does not match transaction")
    if not isinstance(source_page_id, str) or source_page_id not in intent.source_url:
        raise HostBindingBlocked("source page does not match canonical URL")
    if not isinstance(analysis_page_id, str) or analysis_page_id not in intent.analysis_url:
        raise HostBindingBlocked("analysis page does not match canonical URL")
    return execute_journaled_handoff(
        journal=journal, intent=intent, analysis_text=analysis_text,
        modules=modules, destination_confirmed=True,
        registry_complete=registry_complete,
        authorized_write=authorized_write, exclusive_worker=exclusive_worker,
        create_module=create_module, fetch_module=fetch_module)
