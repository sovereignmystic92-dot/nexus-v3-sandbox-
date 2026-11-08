"""Compose authorized byte-exact event preflight with the existing provider handoff.

Host must supply independent authenticated read/write ports and authorization.
This module does not create credentials, triggers, or durable receipts.
"""
from .transcript_event_preflight import validate_event
from .transcript_live_handoff import run_handoff


def execute_event(*, event, raw_source, authorized_event_id, expected_source_ref,
                  notion_page_id, cortex_module_name, analysis,
                  notion_read, notion_write, cortex_read, cortex_write,
                  allow_notion_write=False, allow_cortex_write=False):
    """Reject invalid events before invoking any provider port.

    UTF-8 decoding is strict; source bytes are not normalized. The host is
    responsible for authenticating the event and securing all provider ports.
    """
    proof = validate_event(
        event, raw_source=raw_source, expected_source_ref=expected_source_ref,
        authorized_event_id=authorized_event_id)
    transcript = raw_source.decode("utf-8", errors="strict")
    result = run_handoff(
        transcript=transcript, notion_page_id=notion_page_id,
        cortex_module_name=cortex_module_name, analysis=analysis,
        notion_read=notion_read, notion_write=notion_write,
        cortex_read=cortex_read, cortex_write=cortex_write,
        allow_notion_write=allow_notion_write,
        allow_cortex_write=allow_cortex_write)
    if result.source_sha256 != proof["source_sha256"]:
        raise ValueError("handoff source digest mismatch")
    return result
