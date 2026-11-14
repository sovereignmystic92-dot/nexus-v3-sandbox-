"""Validate GitHub Actions checkpoint provenance before offline reconciliation.

The caller MUST obtain run and artifact metadata through an authenticated,
trusted GitHub API connection. This module cannot authenticate that transport.
"""
import argparse
import hashlib
import json
from pathlib import Path

REPOSITORY = "sovereignmystic92-dot/nexus-v3-sandbox-"
WORKFLOW = "module-evolution-daily-observation.yml"
SCHEMA = "module_evolution_snapshot_v1"
MAX_BYTES = 20 * 1024 * 1024


def verify(metadata, checkpoint_bytes, trusted_digest):
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    required = ("repository", "workflow_path", "run_id", "run_attempt",
                "run_conclusion", "head_sha", "artifact_name", "artifact_expired",
                "artifact_run_id", "artifact_digest")
    if set(metadata) != set(required):
        raise ValueError("unexpected or missing metadata fields")
    if metadata["repository"] != REPOSITORY:
        raise ValueError("wrong repository")
    if metadata["workflow_path"] != ".github/workflows/" + WORKFLOW:
        raise ValueError("wrong workflow")
    if type(metadata["run_id"]) is not int or metadata["run_id"] <= 0:
        raise ValueError("invalid run ID")
    if type(metadata["run_attempt"]) is not int or metadata["run_attempt"] <= 0:
        raise ValueError("invalid attempt")
    if metadata["run_conclusion"] != "success":
        raise ValueError("run not successful")
    sha = metadata["head_sha"]
    if not isinstance(sha, str) or len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("invalid source SHA")
    if metadata["artifact_expired"] is not False:
        raise ValueError("artifact expired")
    if metadata["artifact_run_id"] != metadata["run_id"] or type(metadata["artifact_run_id"]) is not int:
        raise ValueError("artifact belongs to different run")
    expected_name = "nexus-module-daily-{}-{}".format(metadata["run_id"], metadata["run_attempt"])
    if metadata["artifact_name"] != expected_name:
        raise ValueError("unexpected artifact name")
    if not isinstance(checkpoint_bytes, bytes) or len(checkpoint_bytes) > MAX_BYTES:
        raise ValueError("invalid checkpoint bytes")
    actual = hashlib.sha256(checkpoint_bytes).hexdigest()
    if not isinstance(trusted_digest, str) or actual != trusted_digest:
        raise ValueError("checkpoint bytes differ from trusted digest")
    if metadata["artifact_digest"] != "sha256:" + actual:
        raise ValueError("artifact metadata digest mismatch")
    snapshot = json.loads(checkpoint_bytes)
    if not isinstance(snapshot, dict) or set(snapshot) != {"payload", "sha256"}:
        raise ValueError("invalid checkpoint")
    payload = snapshot["payload"]
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise ValueError("invalid checkpoint schema")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if hashlib.sha256(canonical.encode()).hexdigest() != snapshot["sha256"]:
        raise ValueError("checkpoint payload digest mismatch")
    return {"verified_checkpoint_sha256": snapshot["sha256"],
            "verified_file_sha256": actual,
            "run_id": metadata["run_id"],
            "run_attempt": metadata["run_attempt"],
            "head_sha": sha,
            "transport_authenticated": False,
            "readiness_advanced": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--trusted-file-sha256", required=True)
    args = parser.parse_args()
    path = Path(args.checkpoint)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("checkpoint exceeds limit")
    print(json.dumps(verify(json.loads(Path(args.metadata).read_text()),
                            path.read_bytes(), args.trusted_file_sha256), sort_keys=True))


if __name__ == "__main__":
    main()
