"""In-memory source-pinned Notion-to-Gemini composition; no persistence."""
from nexus_sandbox.transcript_event_preflight import validate_event

def review_pinned_source(*, fetch_snapshot, review, event, expected_page_id,
                         expected_revision, authorized_event_id, source_ref,
                         workflow_run_id, workflow_run_attempt, commit_sha):
    """Callbacks are host capabilities, not authentication supplied by this helper."""
    if not all(type(x) is str and x.strip() for x in
               (expected_page_id, expected_revision, authorized_event_id, source_ref)):
        raise ValueError("explicit source bindings required")
    def read():
        value = fetch_snapshot()
        if (type(value) is not dict or set(value) != {"page_id", "revision", "raw"}
                or value["page_id"] != expected_page_id
                or value["revision"] != expected_revision):
            raise ValueError("source identity or revision mismatch")
        validate_event(event, raw_source=value["raw"],
                       expected_source_ref=source_ref, authorized_event_id=authorized_event_id)
        return value
    first = read()
    if read() != first:
        raise ValueError("source changed before review")
    result = review(event=event, raw_source=first["raw"],
                    authorized_event_id=authorized_event_id, expected_source_ref=source_ref)
    if read() != first:
        raise ValueError("source changed during review; no completion receipt")
    # Reuse the receipt constructor as the strict output boundary.
    from nexus_sandbox.transcript_gemini_receipt import make_receipt, verify_expected_receipt
    receipt = make_receipt(result, workflow_run_id=workflow_run_id,
                           workflow_run_attempt=workflow_run_attempt, commit_sha=commit_sha)
    verify_expected_receipt(receipt, event_id=authorized_event_id,
        source_sha256=event["source_sha256"], workflow_run_id=workflow_run_id,
        workflow_run_attempt=workflow_run_attempt, commit_sha=commit_sha)
    return receipt
