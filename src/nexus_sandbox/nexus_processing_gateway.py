"""Unified fail-closed entry point for Nexus-managed transcript processing.

Manual, Gemini, and scheduled jobs use the same authorization and handoff.
The caller supplies trusted provider ports; this module does not acquire tokens,
run Gemini, schedule tasks, or attest external provider identities.
"""
from dataclasses import dataclass
from .transcript_live_handoff import run_handoff

MODES = frozenset(("manual", "gemini", "scheduled"))


@dataclass(frozen=True)
class GatewayResult:
    status: str
    next_action: str
    mode: str
    source_sha256: str = ""
    notion_id: str = ""
    cortex_id: str = ""


def process(*, mode, source_url, transcript, notion_page_id,
            cortex_module_name, analysis, grants, notion_read,
            notion_write, cortex_read, cortex_write):
    if mode not in MODES or type(mode) is not str:
        raise ValueError("Unknown Nexus trigger mode")
    if type(source_url) is not str or not source_url.startswith(
            ("https://www.youtube.com/watch?v=", "https://youtu.be/")):
        raise ValueError("Exact YouTube source URL required")
    if type(grants) is not dict or set(grants) != {
            "process", "notion_write", "cortex_write"} or any(
            type(value) is not bool for value in grants.values()):
        raise ValueError("Explicit exact authorization grants required")
    if not grants["process"]:
        return GatewayResult("BLOCKED", "AUTHORIZE_NEXUS_PROCESSING", mode)
    outcome = run_handoff(
        transcript=transcript, notion_page_id=notion_page_id,
        cortex_module_name=cortex_module_name, analysis=analysis,
        notion_read=notion_read, notion_write=notion_write,
        cortex_read=cortex_read, cortex_write=cortex_write,
        allow_notion_write=grants["notion_write"],
        allow_cortex_write=grants["cortex_write"])
    return GatewayResult(outcome.status, outcome.next_action, mode,
                         outcome.source_sha256, outcome.notion_id,
                         outcome.cortex_id)
