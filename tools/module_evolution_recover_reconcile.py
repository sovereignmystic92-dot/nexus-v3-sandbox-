"""Supervised cross-run checkpoint recovery and offline reconciliation.

No workflow wiring, automatic run discovery, Cortex writes, or readiness promotion.
Requires a caller-selected historical run and explicit read-only GitHub token.
"""
import argparse
import json
import os
from pathlib import Path
import tempfile

from module_evolution_github_transport import recover_run
from module_evolution_reconcile import reconcile


def recover_and_reconcile(run_id, token, event, destination, recovery=recover_run):
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("historical run ID must be positive")
    if not isinstance(token, str) or not token.strip():
        raise ValueError("explicit read-only token required")
    if Path(destination).exists():
        raise ValueError("destination already exists")
    result = recovery(run_id, token)
    if not isinstance(result, dict) or not isinstance(result.get("checkpoint"), bytes):
        raise ValueError("invalid recovery result")
    provenance = result.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("run_id") != run_id:
        raise ValueError("unverified recovery provenance")
    if result.get("archive_digest_verified") is not True:
        raise ValueError("GitHub artifact archive digest required")
    digest = provenance.get("verified_checkpoint_sha256")
    if not isinstance(digest, str):
        raise ValueError("missing verified checkpoint digest")
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "previous.json"
        source.write_bytes(result["checkpoint"])
        receipt = reconcile(source, event, destination, digest)
    return {
        "source_run_id": run_id,
        "source_head_sha": provenance["head_sha"],
        "source_archive_sha256": result["archive_sha256"],
        "source_checkpoint_sha256": digest,
        "reconciliation": receipt,
        "archive_digest_verified": True,
        "readiness_advanced": False,
        "cortex_persisted": False,
        "historical_run_selection": "explicit",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--token-env", default="NEXUS_GITHUB_READ_TOKEN")
    parser.add_argument("--event-file", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.token_env != "NEXUS_GITHUB_READ_TOKEN":
        raise ValueError("only dedicated read-only token environment variable allowed")
    token = os.environ.get(args.token_env, "")
    event = json.loads(Path(args.event_file).read_text(encoding="utf-8"))
    print(json.dumps(recover_and_reconcile(args.run_id, token, event, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
