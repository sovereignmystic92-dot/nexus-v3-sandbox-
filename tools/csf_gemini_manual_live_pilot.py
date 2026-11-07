"""One-shot manual CSF Gemini pilot: metadata-only stdout; no external writes.

The canonical Notion transcript is user-provided, but sending bounded excerpts to
Gemini is an external disclosure and must be explicitly approved at dispatch.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from notion_csf_authenticated_source_probe import PAGE_ID, read_json, children, extract_raw
from nexus_sandbox.csf_transcript_ingest import segment_transcript_bounded
from nexus_sandbox.csf_extractive_proposals import propose_excerpts
from nexus_sandbox.csf_review_packet import prepare_review_packet
from nexus_sandbox.csf_gemini_live_transport import review_with_gemini, GeminiReviewDiagnostic

PINNED_DIGEST = "2f8ba596e3d4672f412487981390de6f3357a5a7156aefbc73a98cc42abcd646"
PINNED_REVISION = "2026-11-07T16:58:00.000Z"


def main():
    if (os.environ.get("NEXUS_CSF_GEMINI_LIVE") != "true"
            or os.environ.get("CSF_GEMINI_SEND_APPROVED") != "true"):
        print('{"status":"BLOCKED","reason":"explicit_approval_required"}')
        return 2
    token = os.environ.get("NOTION_SANDBOX_TOKEN", "")
    if not token or not os.environ.get("GEMINI_API_KEY"):
        print('{"status":"BLOCKED","reason":"credentials_unavailable"}')
        return 2
    try:
        before = read_json("pages/" + PAGE_ID, token)
        if before.get("id", "").replace("-", "") != PAGE_ID.replace("-", "") or before.get("last_edited_time") != PINNED_REVISION:
            raise ValueError("source identity or revision changed")
        raw = extract_raw(children(PAGE_ID, token))
        after = read_json("pages/" + PAGE_ID, token)
        if after.get("last_edited_time") != PINNED_REVISION:
            raise ValueError("source revision changed during read")
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if digest != PINNED_DIGEST:
            raise ValueError("source digest changed")
        bounded = segment_transcript_bounded(PAGE_ID, raw)
        proposals = propose_excerpts(raw, bounded)
        packet = prepare_review_packet(raw, bounded, proposals)
        if packet["review_item_count"] != 12 or bounded["segment_count"] != 17:
            raise ValueError("unexpected source evidence inventory")
        result = review_with_gemini(packet, authorized=True)
        print(json.dumps(result, sort_keys=True))
        return 0
    except GeminiReviewDiagnostic as exc:
        print(json.dumps({"status":"BLOCKED", "reason":"gemini_review",
                          "diagnostic":exc.category, "external_writes":0}))
        return 2
    except Exception as exc:
        # Never print provider error bodies, transcript text or credentials.
        print(json.dumps({"status":"BLOCKED", "reason":"source_or_pilot_validation",
                          "error_type":type(exc).__name__, "external_writes":0}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
