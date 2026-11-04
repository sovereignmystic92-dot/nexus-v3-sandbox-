"""Validate persisted ChatGPT-to-GitHub CP05 evidence and its source binding.

A GitHub commit is a durable observation record, not provider attestation.
Reject missing provenance and any attempt to promote connector observations
into independently authenticated Nexus checkpoint evidence.
"""
from collections.abc import Mapping
from .cp05_chat_github_bridge import validate_chat_github_bridge, BridgeVerdict


def verify_persisted_bridge_evidence(fixture, envelope):
    verdict = validate_chat_github_bridge(fixture, envelope)
    if verdict.status != "OBSERVATIONS_MATCH":
        return verdict
    sources = envelope.get("sources")
    if not isinstance(sources, Mapping):
        return BridgeVerdict("BLOCKED", "MISSING_SOURCE_PROVENANCE")
    if sources.get("notion_page") != (
        "https://app.notion.com/p/" + fixture["notion"]["page_id"].replace("-", "")
    ):
        return BridgeVerdict("BLOCKED", "NOTION_SOURCE_PROVENANCE_MISMATCH")
    if sources.get("cortex_module_id") != fixture["cortex"]["module_id"]:
        return BridgeVerdict("BLOCKED", "CORTEX_SOURCE_PROVENANCE_MISMATCH")
    if envelope.get("evidence_scope") != (
        "ChatGPT connector observations only; Notion verification unverified; "
        "no runtime host identity or complete provider inventory attested"
    ):
        return BridgeVerdict("BLOCKED", "UNTRUSTED_EVIDENCE_SCOPE")
    return BridgeVerdict("OBSERVATIONS_MATCH", "RUNTIME_ATTESTATION_AND_CHECKPOINTS_REQUIRED")
