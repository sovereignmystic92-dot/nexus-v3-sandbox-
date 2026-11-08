"""Prepare a new transcript from UTF-8 stdin without storing or disclosing it."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nexus_sandbox.csf_source_intake import prepare_source

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(8_000_001)
        if len(raw) > 8_000_000:
            raise ValueError("source too large")
        transcript = raw.decode("utf-8", errors="strict")
        result = prepare_source(transcript, document_id=args.document_id, expected_sha256=args.sha256)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, UnicodeError, Exception) as exc:
        # Do not echo source text or exception messages.
        print(json.dumps({"status":"BLOCKED", "reason":"source_validation",
                          "error_type":type(exc).__name__, "external_writes":0}))
        return 2

if __name__ == "__main__":
    sys.exit(main())
