"""Write only a content-free, validated Gemini receipt for GitHub artifact upload."""
import json
import os
import pathlib
import sys
from nexus_sandbox.transcript_gemini_receipt import make_receipt, verify_receipt

def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: write_gemini_review_receipt.py result.json receipt.json")
    source = pathlib.Path(sys.argv[1])
    dest = pathlib.Path(sys.argv[2])
    if source.stat().st_size > 8192:
        raise ValueError("oversized runner metadata")
    result = json.loads(source.read_text(encoding="utf-8"))
    if type(result) is not dict or set(result) != {
        "status", "event_id", "source_sha256", "review_sha256", "model",
        "provider_response_id", "notion_writes", "cortex_writes",
        "durable_receipt_verified"
    }:
        raise ValueError("unexpected runner metadata fields")
    receipt = make_receipt(result, workflow_run_id=os.environ["GITHUB_RUN_ID"],
                           workflow_run_attempt=os.environ["GITHUB_RUN_ATTEMPT"],
                           commit_sha=os.environ["GITHUB_SHA"])
    verify_receipt(receipt)
    dest.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("RECEIPT_CONSTRUCTED_CONTENT_FREE")

if __name__ == "__main__":
    main()
