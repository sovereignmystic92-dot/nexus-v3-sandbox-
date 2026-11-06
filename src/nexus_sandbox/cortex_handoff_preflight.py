"""Pure, fail-closed preflight for a derived-output Cortex handoff.

No connector calls or writes. Caller must provide an independently fetched,
complete destination registry snapshot and explicit destination binding.
"""
from dataclasses import dataclass


class HandoffBlocked(ValueError):
    """No Cortex write is authorized by this preflight."""


@dataclass(frozen=True)
class HandoffDecision:
    status: str
    transaction_key: str
    matched_module: str | None = None


def preflight(*, transaction_key: str, source_url: str, analysis_url: str,
              destination_confirmed: bool, registry_complete: bool,
              modules: list[dict], expected_owner: str) -> HandoffDecision:
    if not all(isinstance(s, str) and s.strip() for s in
               (transaction_key, source_url, analysis_url, expected_owner)):
        raise HandoffBlocked("missing source, transaction or owner binding")
    if not source_url.startswith("https://app.notion.com/p/") or not analysis_url.startswith("https://app.notion.com/p/"):
        raise HandoffBlocked("canonical Notion URLs required")
    if not destination_confirmed or not registry_complete:
        raise HandoffBlocked("destination or registry completeness unverified")
    if not isinstance(modules, list):
        raise HandoffBlocked("registry snapshot required")
    matches = []
    for module in modules:
        if not isinstance(module, dict) or not isinstance(module.get("content"), str):
            raise HandoffBlocked("incomplete module snapshot")
        body = module["content"]
        if transaction_key in body or source_url in body or analysis_url in body:
            matches.append(module)
    if len(matches) > 1:
        raise HandoffBlocked("multiple possible existing modules")
    if matches:
        m = matches[0]
        if m.get("owner") != expected_owner or not m.get("id"):
            raise HandoffBlocked("existing module ownership or identity uncertain")
        return HandoffDecision("RECONCILE_EXISTING_NO_CREATE", transaction_key, m["id"])
    return HandoffDecision("ELIGIBLE_FOR_SEPARATE_AUTHORIZED_CREATE", transaction_key)
