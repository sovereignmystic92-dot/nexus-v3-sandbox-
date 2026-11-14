"""Prepare or replay a CSF review batch on a trusted offline host."""

import argparse
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nexus_sandbox.csf_review_handoff import prepare_handoff, require_batch_review_binding


def read_json(path):
    if not path.is_file():
        raise ValueError("JSON input must be a regular file")
    with path.open("rb") as stream:
        data = stream.read(16_000_001)
    if len(data) > 16_000_000:
        raise ValueError("JSON input is oversized")
    return json.loads(data.decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-envelope", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True,
                        help="SQLite file in a private host directory")
    parser.add_argument("--batch-id", required=True)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--assignments", type=Path, help="Claim ID to candidate JSON mapping")
    inputs.add_argument("--reviews", type=Path, help="Review references for an existing batch")
    args = parser.parse_args()

    try:
        if args.assignments is None and not args.database.is_file():
            raise ValueError("replay requires an existing database")
        source = read_json(args.source_envelope)
        assignments = read_json(args.assignments) if args.assignments is not None else None
        if args.assignments is not None and not isinstance(assignments, dict):
            raise ValueError("assignments must be a JSON object")
        findings = prepare_handoff(args.database, args.batch_id, source, assignments)
        status = "BATCH_PREPARED" if args.assignments is not None else "BATCH_REPLAYED"
        if args.reviews is not None:
            require_batch_review_binding(findings, read_json(args.reviews))
            status = "REVIEW_REFERENCES_MATCH"
    except (OSError, ValueError, TypeError, sqlite3.Error) as exc:
        print(json.dumps({"status": "BLOCKED", "error_type": type(exc).__name__}))
        return 2

    print(json.dumps({
        "status": status,
        "finding_count": len(findings),
        "finding_refs": [
            {"finding_id": item["payload"]["finding_id"], "payload_sha256": item["payload_sha256"]}
            for item in findings
        ],
        "provider_called": False,
        "audit_gate_promoted": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
