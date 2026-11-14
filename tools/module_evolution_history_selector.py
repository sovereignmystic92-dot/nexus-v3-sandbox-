"""Fail-closed selection of the immediately preceding successful Nexus run.

Selection is based on authenticated GitHub API run metadata, never artifact
names or caller-supplied timestamps. No live API calls in this module.
"""
from datetime import datetime, timezone

from module_evolution_artifact_provenance import REPOSITORY, WORKFLOW

WORKFLOW_PATH = ".github/workflows/" + WORKFLOW


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("missing run timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid run timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def select_previous(runs, current_run_id, current_created_at, current_head_branch="main"):
    """Return predecessor ID, or None only when no earlier runs exist.

    Fail closed on pagination truncation, ambiguous timestamps, untrusted
    branches, or an intervening failed/incomplete run. This deliberately
    prevents silent history gaps.
    """
    if type(current_run_id) is not int or current_run_id <= 0:
        raise ValueError("invalid current run")
    if current_head_branch != "main":
        raise ValueError("non-main history prohibited")
    current_time = _timestamp(current_created_at)
    if not isinstance(runs, list):
        raise ValueError("invalid run listing")
    seen = set()
    previous = []
    for run in runs:
        if not isinstance(run, dict) or type(run.get("id")) is not int:
            raise ValueError("invalid run metadata")
        rid = run["id"]
        if rid in seen:
            raise ValueError("duplicate run metadata")
        seen.add(rid)
        if rid == current_run_id:
            continue
        if run.get("repository", {}).get("full_name") != REPOSITORY:
            raise ValueError("unexpected repository in run listing")
        if run.get("path") != WORKFLOW_PATH:
            raise ValueError("unexpected workflow in run listing")
        if run.get("head_branch") != "main":
            continue
        when = _timestamp(run.get("created_at"))
        if when >= current_time:
            continue
        previous.append((when, rid, run))
    if not previous:
        return None
    previous.sort(key=lambda x: (x[0], x[1]), reverse=True)
    top = previous[0][2]
    if top.get("status") != "completed" or top.get("conclusion") != "success":
        raise ValueError("immediate predecessor not successful; manual recovery required")
    if top.get("event") not in ("schedule", "workflow_dispatch"):
        raise ValueError("unexpected predecessor trigger")
    return top["id"]


def select_from_listing(listing, current_run_id, current_created_at):
    """Accept one complete GitHub workflow-runs API response (per_page=100).

    No automatic fallback to empty history when pagination may hide runs.
    """
    if not isinstance(listing, dict) or type(listing.get("total_count")) is not int:
        raise ValueError("invalid workflow listing")
    runs = listing.get("workflow_runs")
    if not isinstance(runs, list) or listing["total_count"] != len(runs):
        raise ValueError("incomplete listing; pagination required before selection")
    return select_previous(runs, current_run_id, current_created_at)
