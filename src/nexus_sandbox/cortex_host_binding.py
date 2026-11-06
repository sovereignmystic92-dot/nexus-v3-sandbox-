"""Read-only host binding validation before any live Cortex handoff.

This checks *supplied evidence*, not the truth of external identity or grants.
The host must independently fetch and attest each binding. No writes here.
"""
from dataclasses import dataclass
from hashlib import sha256


class HostBindingBlocked(ValueError):
    pass


@dataclass(frozen=True)
class HostBinding:
    transaction_key: str
    source_page_id: str
    analysis_page_id: str
    source_revision: str
    analysis_revision: str
    destination_account: str
    destination_owner: str
    registry_digest: str


def validate_host_binding(*, transaction_key, source_page_id, analysis_page_id,
                          source_revision, analysis_revision,
                          destination_account, destination_owner,
                          observed_account, observed_owner,
                          registry_pages, registry_complete, source_verified,
                          analysis_verified, exclusive_worker, durable_journal):
    fields = (transaction_key, source_page_id, analysis_page_id,
              source_revision, analysis_revision, destination_account,
              destination_owner, observed_account, observed_owner)
    if any(not isinstance(x, str) or not x.strip() for x in fields):
        raise HostBindingBlocked("incomplete host identity or revision")
    if source_page_id == analysis_page_id:
        raise HostBindingBlocked("raw source and derived analysis must be distinct")
    if (destination_account != observed_account or
            destination_owner != observed_owner):
        raise HostBindingBlocked("destination account or owner mismatch")
    if not all(x is True for x in (registry_complete, source_verified,
                                  analysis_verified, exclusive_worker,
                                  durable_journal)):
        raise HostBindingBlocked("missing independently established runtime prerequisite")
    if not isinstance(registry_pages, list) or not registry_pages:
        raise HostBindingBlocked("complete registry page evidence required")
    for page in registry_pages:
        if not isinstance(page, dict) or not isinstance(page.get("digest"), str) or len(page["digest"]) != 64:
            raise HostBindingBlocked("registry page digest missing")
        if any(c not in "0123456789abcdef" for c in page["digest"]):
            raise HostBindingBlocked("invalid registry digest")
    digest = sha256("|".join(page["digest"] for page in registry_pages).encode()).hexdigest()
    return HostBinding(transaction_key, source_page_id, analysis_page_id,
                       source_revision, analysis_revision, destination_account,
                       destination_owner, digest)
