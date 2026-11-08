"""Compose source-bound Gemini review with an authorized transcript handoff.

This is an integration seam, not an API client. The host authenticates the
Gemini invocation and all provider ports; a verified review must exist before
either provider write can be attempted.
"""
from .transcript_event_preflight import validate_event
from .transcript_gemini_review import validate_gemini_review
from .transcript_event_execution import execute_event


def execute_reviewed_event(*, event, raw_source, authorized_event_id,
                           expected_source_ref, gemini_review,
                           notion_page_id, cortex_module_name,
                           notion_read, notion_write, cortex_read, cortex_write,
                           allow_notion_write=False, allow_cortex_write=False):
    proof = validate_event(event, raw_source=raw_source,
                           authorized_event_id=authorized_event_id,
                           expected_source_ref=expected_source_ref)
    review = validate_gemini_review(
        gemini_review, source_sha256=proof["source_sha256"],
        source_ref=expected_source_ref)
    result = execute_event(
        event=event, raw_source=raw_source,
        authorized_event_id=authorized_event_id,
        expected_source_ref=expected_source_ref,
        notion_page_id=notion_page_id, cortex_module_name=cortex_module_name,
        analysis=gemini_review.review_text,
        notion_read=notion_read, notion_write=notion_write,
        cortex_read=cortex_read, cortex_write=cortex_write,
        allow_notion_write=allow_notion_write,
        allow_cortex_write=allow_cortex_write)
    return result, review
