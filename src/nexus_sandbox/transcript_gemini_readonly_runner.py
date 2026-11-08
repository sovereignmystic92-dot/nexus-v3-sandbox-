"""Read-only Gemini transcript runner entry point.

Input transcript/event must be staged by an authorized host. This CLI never
fetches a URL, writes to providers, or emits source/review text to stdout.
"""
import argparse
import json
import os
import pathlib
import sys

from .transcript_event_preflight import validate_event
from .transcript_gemini_runtime import invoke_source_bound_gemini
from .transcript_gemini_sdk_port import make_gemini_sdk_port


def run(*, event, raw_source, authorized_event_id, expected_source_ref,
        api_key, model, client_factory=None):
    proof = validate_event(event, raw_source=raw_source,
                           authorized_event_id=authorized_event_id,
                           expected_source_ref=expected_source_ref)
    invoke = make_gemini_sdk_port(api_key=api_key, client_factory=client_factory)
    review = invoke_source_bound_gemini(
        event=event, raw_source=raw_source,
        authorized_event_id=authorized_event_id,
        expected_source_ref=expected_source_ref, model=model, invoke=invoke)
    return {"status": "GEMINI_REVIEW_OBTAINED_READ_ONLY",
            "event_id": proof["event_id"],
            "source_sha256": review.source_sha256,
            "review_sha256": review.review_sha256,
            "model": review.model,
            "provider_response_id": review.invocation_id,
            "notion_writes": 0, "cortex_writes": 0,
            "durable_receipt_verified": False}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-file", required=True)
    parser.add_argument("--source-file", required=True)
    parser.add_argument("--authorized-event-id", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--model", default="gemini-3.5-flash-lite")
    args = parser.parse_args(argv)
    try:
        event = json.loads(pathlib.Path(args.event_file).read_text(encoding="utf-8"))
        source = pathlib.Path(args.source_file).read_bytes()
        result = run(event=event, raw_source=source,
                     authorized_event_id=args.authorized_event_id,
                     expected_source_ref=args.source_ref,
                     api_key=os.environ.get("GEMINI_API_KEY", ""),
                     model=args.model)
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED",
                          "error_type": type(exc).__name__,
                          "notion_writes": 0, "cortex_writes": 0}),
              file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
