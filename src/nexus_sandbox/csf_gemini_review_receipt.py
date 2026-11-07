"""Fail-closed verification of a claimed independent Gemini CSF review receipt.

This validates a receipt's *shape and binding*, not provider authenticity.
Provider execution identity must be checked independently against CI/job evidence.
No network, credentials, LLM calls, or persistence.
"""
import re

HANDOFF_ID = "handoff-2026-11-06-haiti-01"
SOURCE_COMMIT = "8040c01adf9375bac6d06b6ebc91df35509de1c7"
PACKET = "docs/csf/haiti-review-candidates-v0.1.json"


class ReviewReceiptError(ValueError):
    pass


def verify_review_receipt(receipt):
    """Require independently checkable execution references; never grant Gate C."""
    if not isinstance(receipt, dict):
        raise ReviewReceiptError("receipt object required")
    required = {"handoff_id", "source_commit", "payload_ref", "agent",
                "execution_run_url", "response_artifact_sha256", "findings",
                "disagreements", "status"}
    if set(receipt) != required:
        raise ReviewReceiptError("missing or unexpected receipt fields")
    if (receipt["handoff_id"] != HANDOFF_ID or
            receipt["source_commit"] != SOURCE_COMMIT or
            receipt["payload_ref"] != PACKET):
        raise ReviewReceiptError("handoff source binding mismatch")
    if receipt["agent"] != "Gemini-Independent-Analyst":
        raise ReviewReceiptError("unrecognized claimed reviewer")
    url = receipt["execution_run_url"]
    if not isinstance(url, str) or not re.fullmatch(
            r"https://github\.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/[0-9]+", url):
        raise ReviewReceiptError("execution run URL missing or invalid")
    digest = receipt["response_artifact_sha256"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ReviewReceiptError("invalid response artifact digest")
    if receipt["status"] != "REVIEW_SUBMITTED_UNVERIFIED":
        raise ReviewReceiptError("receipt must not self-certify review acceptance")
    for field in ("findings", "disagreements"):
        if not isinstance(receipt[field], list):
            raise ReviewReceiptError("review list required")
    if not receipt["findings"]:
        raise ReviewReceiptError("explicit review findings required")
    for finding in receipt["findings"]:
        if not isinstance(finding, dict) or set(finding) != {
                "finding_id", "severity", "source_path", "counterexample",
                "recommendation", "uncertainty"}:
            raise ReviewReceiptError("incomplete finding evidence")
        if finding["severity"] not in ("critical", "high", "medium", "low", "informational"):
            raise ReviewReceiptError("invalid severity")
        if not all(isinstance(value, str) and value.strip() for value in finding.values()):
            raise ReviewReceiptError("blank finding evidence")
    return True
