"""Read-only reconciliation with the existing transcript coordinator."""
from .supervised_receipt import validate
from .transcript_ingestion import source_id

def reconcile(coordinator, video_id, receipt):
    """Never manufacture verified checkpoints from self-reported receipts."""
    try:
        result = validate(receipt)
        if result["status"] != "RECEIPT_CONSISTENT":
            return result
        key = source_id("youtube", video_id)
        archive = coordinator.get(key, "NOTION_ARCHIVE_VERIFIED")
        source = receipt["source"]
        if not archive or archive.status != "COMPLETE" or not archive.verified:
            raise ValueError("verified archive required")
        evidence = archive.evidence
        if (evidence.get("destination") != "notion:" + source["page_id"]
                or evidence.get("source_revision") != source["revision"]
                or evidence.get("raw_sha256") != source["sha256"]):
            raise ValueError("archive binding mismatch")
        return dict(result, journal_source=key,
                    next_stage=coordinator.next_stage(key),
                    journal_status=coordinator.receipt(key)["status"],
                    provider_writes=0)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return {"status": "FUNCTIONALLY_INCOMPLETE",
                "errors": ["invalid receipt or journal binding"],
                "provider_attestation": False, "automation_ready": False,
                "audit_promotion": False, "provider_writes": 0}
