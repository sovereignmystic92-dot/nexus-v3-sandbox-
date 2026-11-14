"""Bounded scheduled continuity runner, not yet wired into GitHub Actions.

Requires explicit authenticated run metadata and token, fail-closed preflight,
verified artifact recovery, and a new checkpoint destination. No bootstrap.
"""
import argparse
import json
import os
from pathlib import Path

from module_evolution_artifact_provenance import REPOSITORY, WORKFLOW
from module_evolution_github_transport import api_get
from module_evolution_scheduled_preflight import scheduled_history_preflight
from module_evolution_recover_reconcile import recover_and_reconcile


def recover_scheduled(current_run_id, token, event, destination,
                      get=api_get, recover=recover_and_reconcile):
    if type(current_run_id) is not int or current_run_id <= 0:
        raise ValueError("invalid current run")
    if not isinstance(token, str) or not token.strip():
        raise ValueError("explicit read-only token required")
    if not isinstance(event, dict) or event.get("repository") != REPOSITORY:
        raise ValueError("untrusted event repository")
    if event.get("event") != "workflow_run" or event.get("event_id") != str(current_run_id) + "-1":
        raise ValueError("current event identity mismatch")
    if not isinstance(event.get("subject"), str) or len(event["subject"]) != 40 or any(
        c not in "0123456789abcdef" for c in event["subject"]
    ):
        raise ValueError("invalid source SHA")
    expected_url = "https://github.com/" + REPOSITORY + "/actions/runs/" + str(current_run_id)
    if event.get("source_url") != expected_url or event.get("module_hints") != []:
        raise ValueError("invalid event provenance")
    if Path(destination).exists():
        raise ValueError("destination already exists")
    root = "/repos/" + REPOSITORY + "/actions"
    current = get(root + "/runs/" + str(current_run_id), token)
    if not isinstance(current, dict) or current.get("head_sha") != event["subject"]:
        raise ValueError("current run source SHA mismatch")
    listing = get(root + "/workflows/" + WORKFLOW + "/runs?per_page=100&branch=main", token)
    selected = scheduled_history_preflight(current, listing, True)
    previous = selected["previous_run_id"]
    result = recover(previous, token, event, destination)
    if not isinstance(result, dict) or result.get("source_run_id") != previous:
        raise ValueError("recovered predecessor mismatch")
    if result.get("archive_digest_verified") is not True:
        raise ValueError("historical artifact not authenticated")
    if result.get("readiness_advanced") is not False or result.get("cortex_persisted") is not False:
        raise ValueError("unexpected state advancement")
    reconciliation = result.get("reconciliation")
    if not isinstance(reconciliation, dict) or reconciliation.get("new_receipts") != 1:
        raise ValueError("expected exactly one new receipt")
    return {"current_run_id": current_run_id, "previous_run_id": previous,
            "previous_receipts": reconciliation["previous_receipts"],
            "total_receipts": reconciliation["receipts"],
            "checkpoint_sha256": reconciliation["checkpoint_sha256"],
            "historical_artifact_verified": True, "bootstrap_authorized": False,
            "readiness_advanced": False, "cortex_persisted": False,
            "scheduled_recovery_enabled": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--current-run-id", type=int, required=True)
    parser.add_argument("--event-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()
    token = os.environ.get("NEXUS_GITHUB_READ_TOKEN", "")
    event = json.loads(Path(args.event_file).read_text(encoding="utf-8"))
    evidence = recover_scheduled(args.current_run_id, token, event, args.output)
    with Path(args.evidence).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(evidence, sort_keys=True) + "\n")
    print(json.dumps({"current_run_id": evidence["current_run_id"],
                      "previous_run_id": evidence["previous_run_id"],
                      "total_receipts": evidence["total_receipts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
