"""Read-only authenticated GitHub Actions artifact recovery adapter.

Explicit bearer token required; no automatic credential discovery. Uses an
injected transport so tests cannot accidentally access live providers.
Caller must independently authorize repository/workflow identity and ensure
the token has read-only Actions permissions.
"""
import hashlib
import io
import json
import zipfile

from module_evolution_artifact_provenance import verify, REPOSITORY, WORKFLOW

MAX_ARCHIVE = 20 * 1024 * 1024


def recover(run, artifact, archive, expected_run_id):
    """Validate authenticated GitHub API objects and the downloaded artifact ZIP."""
    if not isinstance(run, dict) or not isinstance(artifact, dict):
        raise ValueError("invalid API metadata")
    if type(expected_run_id) is not int or expected_run_id <= 0:
        raise ValueError("invalid expected run")
    if run.get("id") != expected_run_id or run.get("status") != "completed":
        raise ValueError("run identity or status mismatch")
    if run.get("event") not in ("schedule", "workflow_dispatch"):
        raise ValueError("unrecognized workflow trigger")
    if run.get("repository", {}).get("full_name") != REPOSITORY:
        raise ValueError("repository mismatch")
    if run.get("path") != ".github/workflows/" + WORKFLOW:
        raise ValueError("workflow path mismatch")
    if artifact.get("workflow_run", {}).get("id") != expected_run_id:
        raise ValueError("artifact run mismatch")
    if type(artifact.get("id")) is not int or artifact["id"] <= 0:
        raise ValueError("invalid artifact id")
    if not isinstance(archive, bytes) or not 0 < len(archive) <= MAX_ARCHIVE:
        raise ValueError("invalid archive")
    digest = artifact.get("digest")
    if digest is not None and digest != "sha256:" + hashlib.sha256(archive).hexdigest():
        raise ValueError("archive digest mismatch")
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        files = z.infolist()
        if len(files) != 4 or set(f.filename for f in files) != {
            "checkpoint.json", "event.json", "receipt.json", "report.json"
        }:
            raise ValueError("unexpected archive members")
        if any(f.is_dir() or f.file_size > MAX_ARCHIVE or f.compress_size > MAX_ARCHIVE for f in files):
            raise ValueError("oversized or invalid archive member")
        checkpoint = z.read("checkpoint.json")
        if len(checkpoint) > MAX_ARCHIVE:
            raise ValueError("checkpoint exceeds size limit")
    meta = {
        "repository": run["repository"]["full_name"],
        "workflow_path": run["path"],
        "run_id": run["id"],
        "run_attempt": run.get("run_attempt"),
        "run_conclusion": run.get("conclusion"),
        "head_sha": run.get("head_sha"),
        "artifact_name": artifact.get("name"),
        "artifact_expired": artifact.get("expired"),
        "artifact_run_id": artifact["workflow_run"]["id"],
    }
    result = verify(meta, checkpoint, hashlib.sha256(checkpoint).hexdigest())
    return {"checkpoint": checkpoint, "provenance": result,
            "archive_sha256": hashlib.sha256(archive).hexdigest(),
            "archive_digest_verified": digest is not None}


def fetch_and_recover(run_id, token, api_get, archive_get):
    """api_get(path, token)->JSON; archive_get(path, token)->ZIP bytes.

    The supplied transports must authenticate api.github.com, follow signed
    archive redirects without forwarding the token, and enforce HTTPS.
    """
    if not isinstance(token, str) or not token.strip():
        raise ValueError("explicit token required")
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("invalid run id")
    root = "/repos/" + REPOSITORY + "/actions/runs/" + str(run_id)
    run = api_get(root, token)
    artifacts = api_get(root + "/artifacts?per_page=100", token)
    if not isinstance(artifacts, dict) or not isinstance(artifacts.get("artifacts"), list):
        raise ValueError("invalid artifact listing")
    name = "nexus-module-daily-{}-{}".format(run_id, run.get("run_attempt"))
    candidates = [a for a in artifacts["artifacts"] if a.get("name") == name]
    if len(candidates) != 1:
        raise ValueError("missing or ambiguous artifact")
    artifact = candidates[0]
    archive = archive_get("/repos/" + REPOSITORY + "/actions/artifacts/" + str(artifact["id"]) + "/zip", token)
    return recover(run, artifact, archive, run_id)
