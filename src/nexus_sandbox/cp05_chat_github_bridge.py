"""ChatGPT connector observation -> GitHub evidence boundary for CP05.

This is a *manual, supervised* transfer format. ChatGPT connector sessions
cannot be inherited by GitHub Actions. Observations alone never attest Nexus
host identity, complete provider inventory, or CP05 checkpoint completion.
"""
from dataclasses import dataclass
from typing import Mapping
from .cp05_connector_preflight import check_connector_pair


@dataclass(frozen=True)
class BridgeVerdict:
    status: str
    reason: str


def validate_chat_github_bridge(fixture: Mapping, envelope: Mapping) -> BridgeVerdict:
    """Validate sanitized observations without promoting connector access to trust.

    The envelope can be stored in a PR for independent review. No secrets,
    provider credentials, automatic checkpoint writes, or host trust flags
    are accepted from it.
    """
    if not isinstance(envelope, Mapping) or envelope.get("schema") != "nexus.cp05.chat-github-bridge.v1":
        return BridgeVerdict("BLOCKED", "INVALID_BRIDGE_ENVELOPE")
    if envelope.get("execution_mode") != "supervised_read_only":
        return BridgeVerdict("BLOCKED", "INVALID_EXECUTION_MODE")
    if envelope.get("checkpoint_status") != "NOT_ATTESTED":
        return BridgeVerdict("BLOCKED", "CHECKPOINT_CANNOT_BE_ATTESTED_BY_BRIDGE")
    notion, cortex = envelope.get("notion"), envelope.get("cortex")
    if not isinstance(notion, Mapping) or not isinstance(cortex, Mapping):
        return BridgeVerdict("BLOCKED", "MISSING_OBSERVATIONS")
    verdict = check_connector_pair(fixture, notion, cortex)
    if verdict.reason != "HOST_EVIDENCE_REQUIRED":
        return BridgeVerdict("BLOCKED", "UNEXPECTED_PREFLIGHT_VERDICT")
    # Compare identities and payload without ever supplying fabricated host trust.
    for observation, expected in (
        (notion, {"page_id": fixture["notion"]["page_id"],
                  "fixture_id": fixture["notion"]["fixture_id"],
                  "payload": fixture["notion"]["expected_payload"]}),
        (cortex, {"module_id": fixture["cortex"]["module_id"],
                  "source_page_id": fixture["notion"]["page_id"],
                  "payload": fixture["cortex"]["expected_payload"],
                  "version": fixture["cortex"]["version"]}),
    ):
        if any(type(observation.get(k)) is not type(v) or observation.get(k) != v
               for k, v in expected.items()):
            return BridgeVerdict("BLOCKED", "RECONCILE_CONNECTOR_OBSERVATIONS")
    return BridgeVerdict("OBSERVATIONS_MATCH", "REQUIRES_INDEPENDENT_HOST_ATTESTATION")
