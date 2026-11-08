"""Independent post-download receipt verification; no provider credentials."""
import json
import os
import pathlib
import sys
from nexus_sandbox.transcript_gemini_receipt import verify_receipt

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_gemini_review_receipt.py receipt.json")
    path = pathlib.Path(sys.argv[1])
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 8192:
        raise ValueError("missing or unsafe receipt artifact")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    verify_receipt(receipt)
    if (receipt["workflow_run_id"] != os.environ["GITHUB_RUN_ID"] or
        receipt["workflow_run_attempt"] != os.environ["GITHUB_RUN_ATTEMPT"] or
        receipt["commit_sha"] != os.environ["GITHUB_SHA"]):
        raise ValueError("receipt belongs to a different run")
    print("GITHUB_ARTIFACT_READBACK_VERIFIED; NOTION_CORTEX_DURABILITY_UNPROVEN")

if __name__ == "__main__":
    main()
