"""Independent downloaded receipt verification against the pinned source event."""
import argparse
import json
import os
from pathlib import Path
from nexus_sandbox.transcript_event_preflight import validate_event
from nexus_sandbox.transcript_gemini_receipt import verify_expected_receipt


def read_fixture(value):
    path = Path(value)
    root = Path("tests/fixtures").resolve()
    if (path.is_absolute() or not path.is_file() or path.is_symlink()
            or not path.resolve().is_relative_to(root) or path.stat().st_size > 50000):
        raise ValueError("unsafe source fixture")
    with path.open("rb") as stream:
        raw = stream.read(50001)
    if len(raw) > 50000:
        raise ValueError("oversized source fixture")
    return raw


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt")
    parser.add_argument("--event-file", required=True)
    parser.add_argument("--source-file", required=True)
    parser.add_argument("--authorized-event-id", required=True)
    parser.add_argument("--source-ref", required=True)
    args = parser.parse_args(argv)
    path = Path(args.receipt)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 8192:
        raise ValueError("missing or unsafe receipt artifact")
    raw = path.read_bytes()
    if len(raw) > 8192:
        raise ValueError("oversized receipt artifact")
    receipt = json.loads(raw)
    proof = validate_event(json.loads(read_fixture(args.event_file)),
                           raw_source=read_fixture(args.source_file),
                           authorized_event_id=args.authorized_event_id,
                           expected_source_ref=args.source_ref)
    verify_expected_receipt(
        receipt, event_id=proof["event_id"], source_sha256=proof["source_sha256"],
        workflow_run_id=os.environ["GITHUB_RUN_ID"],
        workflow_run_attempt=os.environ["GITHUB_RUN_ATTEMPT"],
        commit_sha=os.environ["GITHUB_SHA"])
    print("GITHUB_ARTIFACT_SOURCE_BOUND_READBACK_VERIFIED; NOTION_CORTEX_DURABILITY_UNPROVEN")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit("BLOCKED: receipt or source context did not verify")
