"""Verify downloaded Gemini response bytes against a claimed review receipt.

This does NOT authenticate Gemini or GitHub; an independent reviewer must
verify workflow job identity and actual model invocation separately.
"""
import hashlib
import json
from .csf_gemini_review_receipt import ReviewReceiptError, verify_review_receipt

MAX_RESPONSE_BYTES = 100_000


def verify_review_artifact(receipt, artifact_bytes):
    verify_review_receipt(receipt)
    if not isinstance(artifact_bytes, bytes) or not artifact_bytes or len(artifact_bytes) > MAX_RESPONSE_BYTES:
        raise ReviewReceiptError("missing or oversized response artifact")
    digest = hashlib.sha256(artifact_bytes).hexdigest()
    if digest != receipt["response_artifact_sha256"]:
        raise ReviewReceiptError("response artifact hash mismatch")
    try:
        response = json.loads(artifact_bytes.decode("utf-8", errors="strict"))
    except (UnicodeError, ValueError) as error:
        raise ReviewReceiptError("response artifact is not valid UTF-8 JSON") from error
    if not isinstance(response, dict) or set(response) != {"handoff_id", "source_commit", "findings", "disagreements"}:
        raise ReviewReceiptError("response artifact envelope mismatch")
    if response["handoff_id"] != receipt["handoff_id"] or response["source_commit"] != receipt["source_commit"]:
        raise ReviewReceiptError("response artifact source mismatch")
    if response["findings"] != receipt["findings"] or response["disagreements"] != receipt["disagreements"]:
        raise ReviewReceiptError("response artifact findings mismatch")
    return True
