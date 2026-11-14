"""Fail-closed preflight for future scheduled historical recovery.

This is a pure decision function: it never authorizes bootstrap, fetches data,
writes checkpoints, or changes readiness. Scheduling remains separately gated.
"""
from module_evolution_artifact_provenance import REPOSITORY, WORKFLOW


def scheduled_history_preflight(run, listing, token_present):
    """Return the bounded candidate predecessor or reject without side effects."""
    if token_present is not True:
        raise ValueError("dedicated read-only token unavailable")
    if not isinstance(run, dict) or type(run.get("id")) is not int or run["id"] <= 0:
        raise ValueError("invalid current run")
    if run.get("repository", {}).get("full_name") != REPOSITORY:
        raise ValueError("repository mismatch")
    if run.get("path") != ".github/workflows/" + WORKFLOW:
        raise ValueError("workflow mismatch")
    if run.get("head_branch") != "main" or run.get("event") not in ("schedule", "workflow_dispatch"):
        raise ValueError("unsupported run origin")
    if run.get("run_attempt") != 1:
        raise ValueError("rerun requires supervised recovery")
    if run.get("status") not in ("queued", "in_progress", "completed"):
        raise ValueError("invalid run status")
    if not isinstance(run.get("created_at"), str) or not run["created_at"]:
        raise ValueError("missing creation timestamp")
    if not isinstance(listing, dict) or type(listing.get("total_count")) is not int:
        raise ValueError("invalid run listing")
    if listing["total_count"] > 100:
        raise ValueError("history exceeds bounded discovery window")
    from module_evolution_history_selector import select_from_listing
    previous = select_from_listing(listing, run["id"], run["created_at"])
    if previous is None:
        raise ValueError("no predecessor: explicit trusted bootstrap required")
    if type(previous) is not int or previous <= 0 or previous >= run["id"]:
        raise ValueError("invalid predecessor")
    return {"current_run_id": run["id"], "previous_run_id": previous,
            "bootstrap_authorized": False, "readiness_advanced": False,
            "cortex_persisted": False, "scheduled_recovery_enabled": False}
