"""Independent offline readback of the manual continuity rehearsal ZIP.

Caller supplies the downloaded ZIP and an independently trusted GitHub artifact
digest. This module performs no network requests or readiness promotion.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

from module_evolution_artifact_provenance import verify, REPOSITORY, WORKFLOW

MAX_ZIP = 20 * 1024 * 1024


def verify_rehearsal(archive, expected_zip_sha256, source_run):
    if not isinstance(archive, bytes) or not 0 < len(archive) <= MAX_ZIP:
        raise ValueError("invalid ZIP size")
    if not isinstance(expected_zip_sha256, str) or len(expected_zip_sha256) != 64:
        raise ValueError("trusted ZIP digest required")
    if hashlib.sha256(archive).hexdigest() != expected_zip_sha256:
        raise ValueError("rehearsal ZIP digest mismatch")
    if not isinstance(source_run, dict) or type(source_run.get("id")) is not int:
        raise ValueError("trusted source run metadata required")
    if source_run.get("repository", {}).get("full_name") != REPOSITORY:
        raise ValueError("source repository mismatch")
    if source_run.get("path") != ".github/workflows/" + WORKFLOW:
        raise ValueError("source workflow mismatch")
    if source_run.get("status") != "completed" or source_run.get("conclusion") != "success":
        raise ValueError("source run unsuccessful")
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        files = z.infolist()
        if len(files) != 2 or {f.filename for f in files} != {"checkpoint.json", "evidence.json"}:
            raise ValueError("unexpected rehearsal ZIP members")
        if any(f.is_dir() or f.file_size > MAX_ZIP or f.compress_size > MAX_ZIP for f in files):
            raise ValueError("oversized rehearsal member")
        checkpoint = z.read("checkpoint.json")
        evidence = json.loads(z.read("evidence.json"))
    if not isinstance(evidence, dict) or set(evidence) != {
        "evidence_class", "source_run_id", "source_head_sha",
        "checkpoint_sha256", "archive_sha256", "readiness_advanced",
        "cortex_persisted", "scheduled_recovery_enabled"
    }:
        raise ValueError("invalid rehearsal evidence")
    if evidence["evidence_class"] != "manual_rehearsal":
        raise ValueError("wrong evidence class")
    if evidence["source_run_id"] != source_run["id"] or evidence["source_head_sha"] != source_run.get("head_sha"):
        raise ValueError("source run mismatch")
    if any(evidence[key] is not False for key in (
        "readiness_advanced", "cortex_persisted", "scheduled_recovery_enabled"
    )):
        raise ValueError("unexpected state promotion")
    digest = evidence["checkpoint_sha256"]
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("invalid checkpoint digest")
    if not isinstance(evidence["archive_sha256"], str) or len(evidence["archive_sha256"]) != 64:
        raise ValueError("invalid predecessor archive digest")
    metadata = {
        "repository": REPOSITORY, "workflow_path": source_run["path"],
        "run_id": source_run["id"], "run_attempt": source_run.get("run_attempt"),
        "run_conclusion": source_run["conclusion"], "head_sha": source_run["head_sha"],
        "artifact_name": "nexus-module-daily-{}-{}".format(source_run["id"], source_run.get("run_attempt")),
        "artifact_expired": False, "artifact_run_id": source_run["id"],
    }
    checked = verify(metadata, checkpoint, hashlib.sha256(checkpoint).hexdigest())
    if checked["verified_checkpoint_sha256"] != digest:
        raise ValueError("checkpoint payload digest mismatch")
    return {"evidence_class": "independent_rehearsal_readback",
            "source_run_id": source_run["id"],
            "rehearsal_zip_sha256": expected_zip_sha256,
            "checkpoint_sha256": digest,
            "archive_digest_evidence_recorded": True,
            "readiness_advanced": False, "cortex_persisted": False,
            "scheduled_recovery_enabled": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True)
    parser.add_argument("--trusted-zip-sha256", required=True)
    parser.add_argument("--source-run-json", required=True)
    args = parser.parse_args()
    path = Path(args.zip)
    if path.stat().st_size > MAX_ZIP:
        raise ValueError("ZIP exceeds size limit")
    print(json.dumps(verify_rehearsal(path.read_bytes(), args.trusted_zip_sha256,
                                     json.loads(Path(args.source_run_json).read_text())),
                     sort_keys=True))


if __name__ == "__main__":
    main()
