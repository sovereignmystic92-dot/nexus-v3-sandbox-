"""Read-only CP05 provider probe, with injected authenticated host readers.

Readers must perform fresh provider requests with least-privilege credentials,
return complete observations, and attest identity/pagination. This module
never writes to either provider or advances a Nexus checkpoint.
"""
from dataclasses import dataclass
from typing import Callable, Mapping

from .cp05_connector_preflight import check_connector_pair
from .cp05_runtime_capabilities import check_runtime_capabilities


@dataclass(frozen=True)
class ReadProbeResult:
    status: str
    reason: str


def probe_cp05_read_only(*, fixture: Mapping, notion_reader: Callable,
                         cortex_reader: Callable, environ=None,
                         capabilities=None) -> ReadProbeResult:
    """Read providers once each; fail closed on errors or incomplete attestation.

    Readers return (observation, metadata). Metadata MUST be derived from
    provider authentication and complete-pagination verification, not fixture
    fields. Do not log credentials, raw responses, or exception messages.
    """
    readiness = check_runtime_capabilities(
        environ=environ, capabilities=capabilities)
    if readiness.status != "READY_FOR_AUTHENTICATED_READ_PROBE":
        return ReadProbeResult("BLOCKED", "RUNTIME_CAPABILITIES_MISSING")
    if not callable(notion_reader) or not callable(cortex_reader):
        return ReadProbeResult("BLOCKED", "PROVIDER_READERS_REQUIRED")
    try:
        notion, notion_meta = notion_reader(fixture["notion"]["page_id"])
        cortex, cortex_meta = cortex_reader(fixture["cortex"]["module_id"])
    except Exception:
        return ReadProbeResult("BLOCKED", "PROVIDER_READ_FAILED")
    if not all(isinstance(x, Mapping) for x in
               (notion, notion_meta, cortex, cortex_meta)):
        return ReadProbeResult("BLOCKED", "INVALID_PROVIDER_RESPONSE")
    trust = {
        "notion_authenticated": notion_meta.get("authenticated") is True,
        "notion_complete": notion_meta.get("complete_inventory") is True,
        "cortex_authenticated": cortex_meta.get("authenticated") is True,
        "cortex_complete": cortex_meta.get("complete_inventory") is True,
    }
    verdict = check_connector_pair(fixture, notion, cortex, **trust)
    if verdict.status != "MATCHED":
        return ReadProbeResult("BLOCKED", verdict.reason)
    return ReadProbeResult("READ_ONLY_MATCH", "NO_CHECKPOINT_WRITE_AUTHORIZED")
