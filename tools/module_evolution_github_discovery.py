"""Authenticated, bounded historical workflow discovery for Nexus.

No credential acquisition, writes, workflow scheduling, or implicit bootstrap.
The caller supplies an explicit read-only token and current run identity.
"""
from module_evolution_artifact_provenance import REPOSITORY, WORKFLOW
from module_evolution_history_selector import select_from_listing
from module_evolution_github_transport import api_get

MAX_RUNS = 100


def discover_previous(current_run_id, token, get=api_get):
    if type(current_run_id) is not int or current_run_id <= 0:
        raise ValueError("invalid current run id")
    if not isinstance(token, str) or not token.strip():
        raise ValueError("explicit read-only token required")
    root = "/repos/" + REPOSITORY + "/actions"
    current = get(root + "/runs/" + str(current_run_id), token)
    if not isinstance(current, dict) or current.get("id") != current_run_id:
        raise ValueError("current run identity mismatch")
    if current.get("repository", {}).get("full_name") != REPOSITORY:
        raise ValueError("current run repository mismatch")
    if current.get("path") != ".github/workflows/" + WORKFLOW:
        raise ValueError("current run workflow mismatch")
    if current.get("head_branch") != "main":
        raise ValueError("current run must be on main")
    if current.get("event") not in ("schedule", "workflow_dispatch"):
        raise ValueError("unsupported current trigger")
    created = current.get("created_at")
    if not isinstance(created, str) or not created:
        raise ValueError("missing current run creation time")
    listing = get(root + "/workflows/" + WORKFLOW + "/runs?per_page=100&branch=main", token)
    if not isinstance(listing, dict) or type(listing.get("total_count")) is not int:
        raise ValueError("invalid run listing")
    if listing["total_count"] > MAX_RUNS:
        raise ValueError("historical listing exceeds bounded window; manual recovery required")
    previous = select_from_listing(listing, current_run_id, created)
    if previous is None:
        # Empty history is NOT proof that the repository is new or safe to bootstrap.
        raise ValueError("no predecessor found; explicit trusted bootstrap required")
    if previous >= current_run_id:
        raise ValueError("unexpected predecessor run id ordering")
    return {"current_run_id": current_run_id, "previous_run_id": previous,
            "discovery_authenticated": True, "bootstrap_authorized": False,
            "readiness_advanced": False, "cortex_persisted": False}
