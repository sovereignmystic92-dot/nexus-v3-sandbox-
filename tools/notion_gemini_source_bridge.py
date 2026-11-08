"""Manual in-memory real-source bridge. No source files, provider writes or retries."""
import argparse
from functools import partial
import json
import os
from pathlib import Path
import sys
import notion_csf_authenticated_source_probe as notion

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nexus_sandbox.notion_gemini_source_bridge import review_pinned_source
from nexus_sandbox.transcript_gemini_readonly_runner import run

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-file", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--source-ref", required=True)
    args = parser.parse_args()
    try:
        if os.environ.get("NEXUS_REAL_SOURCE_GEMINI_APPROVED") != "true":
            raise ValueError("explicit real-source disclosure approval required")
        token = os.environ.get("NOTION_SANDBOX_TOKEN", "")
        key = os.environ.get("GEMINI_API_KEY", "")
        if not token or not key:
            raise ValueError("missing credentials")
        path = Path(args.event_file)
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 8192:
            raise ValueError("unsafe event")
        event = json.loads(path.read_bytes())
        def fetch():
            page = notion.read_json("pages/" + notion.PAGE_ID, token)
            if page.get("archived") or page.get("in_trash"):
                raise ValueError("source unavailable")
            if page.get("id", "").replace("-", "") != notion.PAGE_ID.replace("-", ""):
                raise ValueError("source identity mismatch")
            raw = notion.extract_raw(notion.children(notion.PAGE_ID, token)).encode("utf-8")
            again = notion.read_json("pages/" + notion.PAGE_ID, token)
            if again != page:
                raise ValueError("metadata changed during source retrieval")
            return dict(page_id=notion.PAGE_ID, revision=page.get("last_edited_time"), raw=raw)
        receipt = review_pinned_source(
            fetch_snapshot=fetch, review=partial(run, api_key=key, model="gemini-3.5-flash-lite"),
            event=event, expected_page_id=notion.PAGE_ID, expected_revision=args.source_revision.strip(),
            authorized_event_id=args.event_id, source_ref=args.source_ref,
            workflow_run_id=os.environ["GITHUB_RUN_ID"],
            workflow_run_attempt=os.environ["GITHUB_RUN_ATTEMPT"], commit_sha=os.environ["GITHUB_SHA"])
        print(json.dumps(receipt, sort_keys=True))
        return 0
    except Exception:
        print('{"status":"BLOCKED","reason":"source_or_review_not_verified"}', file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
