"""Independently validate a supervised two-run evidence ZIP.

Pure offline validator: no credentials, network access, writes, or readiness changes.
"""
import hashlib
import io
import json
import re
import zipfile


def validate_evidence(archive, expected_zip_sha256):
    if not isinstance(archive, bytes) or len(archive) > 20 * 1024 * 1024:
        raise ValueError("invalid archive bytes")
    if not isinstance(expected_zip_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_zip_sha256):
        raise ValueError("invalid expected ZIP digest")
    if hashlib.sha256(archive).hexdigest() != expected_zip_sha256:
        raise ValueError("ZIP digest mismatch")
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        if sorted(z.namelist()) != ["checkpoint.json", "evidence.json"]:
            raise ValueError("unexpected archive members")
        if any(x.file_size > 1024 * 1024 or x.is_dir() for x in z.infolist()):
            raise ValueError("oversized or directory member")
        checkpoint = json.loads(z.read("checkpoint.json"))
        evidence = json.loads(z.read("evidence.json"))
    payload = checkpoint.get("payload")
    if not isinstance(payload, dict) or payload.get("schema") != "module_evolution_snapshot_v1":
        raise ValueError("unexpected checkpoint schema")
    from module_evolution_snapshot import canonical_bytes
    digest = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    if checkpoint.get("sha256") != digest or evidence.get("checkpoint_sha256") != digest:
        raise ValueError("checkpoint integrity mismatch")
    receipts = payload.get("receipts")
    if not isinstance(receipts, list) or len(receipts) != 2:
        raise ValueError("expected exactly two receipts")
    if len({r.get("event_key") for r in receipts}) != 2:
        raise ValueError("duplicate receipt keys")
    events = [json.loads(r["event_json"]) for r in receipts]
    previous, target = evidence.get("previous_run_id"), evidence.get("target_run_id")
    if type(previous) is not int or type(target) is not int or previous >= target:
        raise ValueError("invalid run ordering")
    if [e.get("event_id") for e in events] != [str(previous) + "-1", str(target) + "-1"]:
        raise ValueError("run receipts do not match evidence")
    if any(e.get("repository") != "sovereignmystic92-dot/nexus-v3-sandbox-" or
           e.get("event") != "workflow_run" for e in events):
        raise ValueError("invalid event provenance")
    if any(r.get("status") != "PENDING_VALIDATION" for r in receipts):
        raise ValueError("unexpected readiness state")
    if (evidence.get("previous_receipts"), evidence.get("new_receipts"), evidence.get("total_receipts")) != (1, 1, 2):
        raise ValueError("invalid receipt accounting")
    if evidence.get("evidence_class") != "supervised_live" or any(evidence.get(k) is not False for k in
        ("cortex_persisted", "readiness_advanced", "unattended_enabled")):
        raise ValueError("unsupported evidence claims")
    return {"previous_run_id": previous, "target_run_id": target, "receipts": 2,
            "zip_sha256": expected_zip_sha256, "checkpoint_sha256": digest,
            "readiness_advanced": False, "unattended_enabled": False}
