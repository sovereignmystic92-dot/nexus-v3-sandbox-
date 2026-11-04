"""CP05 connector observation boundary: never infer runtime trust from fixtures.

This adapter accepts a frozen fixture and separately supplied host evidence.
It is deliberately provider-neutral: connector observations are not credentials,
provider transaction locks, or independent runtime attestation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ObservationVerdict:
    status: str
    reason: str


def check_connector_pair(fixture: Mapping, notion: Mapping, cortex: Mapping,
                         *, notion_authenticated: bool = False,
                         cortex_authenticated: bool = False,
                         notion_complete: bool = False,
                         cortex_complete: bool = False) -> ObservationVerdict:
    """Validate identity/content and fail closed until host assertions are proven.

    The four boolean flags MUST come from a trusted runtime host after fresh
    provider requests; they MUST NOT be populated from fixture JSON.
    This is a preflight check, not an authorization or checkpoint write.
    """
    if any(type(v) is not bool for v in (
            notion_authenticated, cortex_authenticated,
            notion_complete, cortex_complete)):
        return ObservationVerdict("BLOCKED", "INVALID_HOST_ASSERTION")
    if not all((notion_authenticated, cortex_authenticated,
                notion_complete, cortex_complete)):
        return ObservationVerdict("BLOCKED", "HOST_EVIDENCE_REQUIRED")
    if not all(isinstance(x, Mapping) for x in (fixture, notion, cortex)):
        return ObservationVerdict("BLOCKED", "INVALID_INPUT")
    source = fixture.get("notion")
    output = fixture.get("cortex")
    if not isinstance(source, Mapping) or not isinstance(output, Mapping):
        return ObservationVerdict("BLOCKED", "INVALID_FIXTURE")
    fields = (
        (notion, "page_id", source.get("page_id")),
        (notion, "fixture_id", source.get("fixture_id")),
        (notion, "payload", source.get("expected_payload")),
        (cortex, "module_id", output.get("module_id")),
        (cortex, "source_page_id", source.get("page_id")),
        (cortex, "payload", output.get("expected_payload")),
    )
    if any(type(expected) is not str or not expected or
           type(observed.get(key)) is not str or observed[key] != expected
           for observed, key, expected in fields):
        return ObservationVerdict("BLOCKED", "RECONCILE_PROVIDER_OBSERVATIONS")
    if type(cortex.get("version")) is not int or cortex["version"] != output.get("version"):
        return ObservationVerdict("BLOCKED", "RECONCILE_CORTEX_VERSION")
    return ObservationVerdict("MATCHED", "PREFLIGHT_ONLY_REQUIRE_CHECKPOINT_PREREQUISITES")
