"""Build a verified daily-run observation from authenticated GitHub metadata.

This is for supervised read-only verification, not scheduled processing.
"""
import argparse
import json
import os
from pathlib import Path

from module_evolution_artifact_provenance import REPOSITORY, WORKFLOW
from module_evolution_github_transport import api_get
from module_evolution_supervised_continuity import continue_history


def verify_two_run_continuity(run_id, token, destination, get=api_get,
                              continuity=continue_history):
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("invalid target run id")
    if not isinstance(token, str) or not token.strip():
        raise ValueError("explicit read-only token required")
    run = get("/repos/" + REPOSITORY + "/actions/runs/" + str(run_id), token)
    if not isinstance(run, dict) or run.get("id") != run_id:
        raise ValueError("target run identity mismatch")
    if run.get("repository", {}).get("full_name") != REPOSITORY:
        raise ValueError("repository mismatch")
    if run.get("path") != ".github/workflows/" + WORKFLOW:
        raise ValueError("workflow mismatch")
    if run.get("head_branch") != "main" or run.get("status") != "completed" or run.get("conclusion") != "success":
        raise ValueError("target daily run must be successful on main")
    if run.get("run_attempt") != 1 or run.get("event") not in ("schedule", "workflow_dispatch"):
        raise ValueError("only original successful daily attempts supported")
    sha = run.get("head_sha")
    if not isinstance(sha, str) or len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("invalid source SHA")
    event = {"repository": REPOSITORY, "event": "workflow_run",
             "event_id": str(run_id) + "-1", "subject": sha,
             "source_url": "https://github.com/" + REPOSITORY + "/actions/runs/" + str(run_id),
             "module_hints": []}
    result = continuity(run_id, token, event, destination)
    receipt = result.get("recovery", {}).get("reconciliation", {})
    if receipt.get("previous_receipts", 0) < 1 or receipt.get("new_receipts") != 1:
        raise ValueError("two-run continuity not demonstrated")
    return {"target_run_id": run_id, "previous_run_id": result["previous_run_id"],
            "previous_receipts": receipt["previous_receipts"],
            "new_receipts": receipt["new_receipts"], "total_receipts": receipt["receipts"],
            "checkpoint_sha256": receipt["checkpoint_sha256"],
            "readiness_advanced": False, "cortex_persisted": False,
            "unattended_enabled": False, "evidence_class": "supervised_live"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--current-run-id", type=int, required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--evidence", required=True)
    args = p.parse_args()
    token = os.environ.get("NEXUS_GITHUB_READ_TOKEN", "")
    result = verify_two_run_continuity(args.current_run_id, token, args.output)
    Path(args.evidence).write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"target_run_id": result["target_run_id"], "previous_run_id": result["previous_run_id"],
                      "total_receipts": result["total_receipts"], "evidence_class": result["evidence_class"]}))


if __name__ == "__main__":
    main()
