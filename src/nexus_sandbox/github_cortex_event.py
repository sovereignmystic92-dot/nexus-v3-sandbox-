"""Strict, side-effect-free GitHub Actions event envelope for Cortex sync.

This module does NOT write to Cortex or authenticate GitHub webhook payloads.
The host must obtain an authenticated GitHub API observation and provide durable
single-writer journaling and Cortex readback before promoting any record.
"""
import hashlib
import json
import re

REPOSITORY = "sovereignmystic92-dot/nexus-v3-sandbox-"
SHA = re.compile(r"^[0-9a-f]{40}$")
CONCLUSIONS = {"success", "failure", "cancelled", "timed_out", "action_required",
               "neutral", "skipped", "stale", "startup_failure"}


def normalize_run(run, repository=REPOSITORY):
    """Return a deterministic, bounded envelope; reject incomplete observations."""
    if type(run) is not dict or repository != REPOSITORY:
        raise ValueError("Unexpected repository")
    if run.get("repository", {}).get("full_name") != repository:
        raise ValueError("Repository identity mismatch")
    run_id, attempt = run.get("id"), run.get("run_attempt")
    sha, conclusion = run.get("head_sha"), run.get("conclusion")
    if (type(run_id) is not int or run_id <= 0 or
            type(attempt) is not int or attempt <= 0 or
            type(sha) is not str or not SHA.fullmatch(sha) or
            conclusion not in CONCLUSIONS or
            run.get("status") != "completed"):
        raise ValueError("Incomplete or nonterminal workflow observation")
    workflow = run.get("workflow_id")
    if type(workflow) is not int or workflow <= 0:
        raise ValueError("Missing workflow identity")
    expected_url = f"https://github.com/{repository}/actions/runs/{run_id}"
    if run.get("html_url") != expected_url:
        raise ValueError("Untrusted run URL")
    payload = {
        "schema": "NEXUS_GITHUB_RUN_V1",
        "repository": repository,
        "run_id": run_id,
        "attempt": attempt,
        "workflow_id": workflow,
        "commit_sha": sha,
        "conclusion": conclusion,
        "run_url": expected_url,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    payload["digest_sha256"] = hashlib.sha256(canonical.encode("ascii")).hexdigest()
    payload["event_key"] = f"github-run:{run_id}:attempt:{attempt}"
    return payload
