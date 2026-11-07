"""CP03/CP04 trigger evidence: no external credentials or writes required."""
import json
import os
from datetime import datetime, timezone

def receipt(event_name, run_id, attempt, sha):
    allowed = {"workflow_dispatch", "schedule", "repository_dispatch"}
    if event_name not in allowed:
        raise ValueError("Unsupported event")
    if not str(run_id).isdigit() or not str(attempt).isdigit():
        raise ValueError("Invalid GitHub run identity")
    return {
        "schema": "nexus.audit.trigger_receipt.v1",
        "gate_scope": ["CP03", "CP04"],
        "status": "OBSERVED_TRIGGER_ONLY",
        "audit_pass": False,
        "event": event_name,
        "run_id": str(run_id),
        "run_attempt": str(attempt),
        "commit_sha": sha,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider_writes": 0,
        "external_credentials_used": False,
    }

if __name__ == "__main__":
    result = receipt(
        os.environ["GITHUB_EVENT_NAME"],
        os.environ["GITHUB_RUN_ID"],
        os.environ["GITHUB_RUN_ATTEMPT"],
        os.environ["GITHUB_SHA"],
    )
    print(json.dumps(result, sort_keys=True))
