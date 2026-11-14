"""Supervised composition of authenticated discovery, recovery and reconciliation.

This entrypoint does not run in scheduled Actions, bootstrap history, provision
credentials, write Cortex, or promote readiness. Discovery and recovery must
both succeed before the destination checkpoint can be created.
"""
import argparse
import json
import os
from pathlib import Path

from module_evolution_github_discovery import discover_previous
from module_evolution_recover_reconcile import recover_and_reconcile


def continue_history(current_run_id, token, event, destination,
                     discovery=discover_previous, recovery_reconcile=recover_and_reconcile):
    if type(current_run_id) is not int or current_run_id <= 0:
        raise ValueError("invalid current run")
    if not isinstance(token, str) or not token.strip():
        raise ValueError("explicit read-only token required")
    if not isinstance(event, dict):
        raise ValueError("event must be an object")
    if event.get("event") != "workflow_run":
        raise ValueError("unsupported continuity event")
    if event.get("event_id") not in (str(current_run_id), str(current_run_id) + "-1"):
        raise ValueError("event does not match current run's first attempt")
    if Path(destination).exists():
        raise ValueError("destination already exists")
    selected = discovery(current_run_id, token)
    if not isinstance(selected, dict):
        raise ValueError("invalid discovery result")
    if selected.get("current_run_id") != current_run_id or selected.get("discovery_authenticated") is not True:
        raise ValueError("discovery provenance missing")
    if selected.get("bootstrap_authorized") is not False:
        raise ValueError("unexpected bootstrap authorization")
    previous = selected.get("previous_run_id")
    if type(previous) is not int or previous <= 0 or previous >= current_run_id:
        raise ValueError("invalid predecessor")
    result = recovery_reconcile(previous, token, event, destination)
    if not isinstance(result, dict) or result.get("source_run_id") != previous:
        raise ValueError("recovery predecessor mismatch")
    if result.get("archive_digest_verified") is not True:
        raise ValueError("archive digest verification missing")
    if result.get("readiness_advanced") is not False or result.get("cortex_persisted") is not False:
        raise ValueError("unexpected provider advancement")
    return {
        "current_run_id": current_run_id,
        "previous_run_id": previous,
        "historical_selection": "authenticated_discovery",
        "recovery": result,
        "readiness_advanced": False,
        "cortex_persisted": False,
        "unattended_enabled": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--current-run-id", type=int, required=True)
    parser.add_argument("--token-env", default="NEXUS_GITHUB_READ_TOKEN")
    parser.add_argument("--event-file", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.token_env != "NEXUS_GITHUB_READ_TOKEN":
        raise ValueError("only dedicated read-only token environment variable allowed")
    event = json.loads(Path(args.event_file).read_text(encoding="utf-8"))
    result = continue_history(args.current_run_id, os.environ.get(args.token_env, ""), event, args.output)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
