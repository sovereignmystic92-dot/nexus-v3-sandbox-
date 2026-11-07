"""Host-bound Nexus execution with durable, non-attesting receipt.

Provider ports must come from an authenticated host. This module cannot prove
their origin and therefore never emits VERIFIED or promotes an audit gate.
"""
import json
import os
from pathlib import Path

from .nexus_processing_gateway import process


def execute(*, run_id, receipt_dir, provider_ports, **job):
    if type(run_id) is not str or not run_id or len(run_id) > 120 or not all(
            c.isalnum() or c in "-_" for c in run_id):
        raise ValueError("Invalid immutable run identifier")
    if type(provider_ports) is not dict or set(provider_ports) != {
            "notion_read", "notion_write", "cortex_read", "cortex_write"} or not all(
            callable(p) for p in provider_ports.values()):
        raise ValueError("Four explicit provider ports required")
    directory = Path(receipt_dir)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Existing nonsymlink receipt directory required")
    target = directory / (run_id + ".json")
    if target.exists() or target.is_symlink():
        raise FileExistsError("Run receipt already exists; reconcile before retry")
    # Reserve the run identifier BEFORE any provider side effect. A crash leaves
    # a marker that requires explicit reconciliation, never an automatic retry.
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as marker:
        marker.write(b'{"status":"INCOMPLETE","next_action":"RECONCILE_UNCERTAIN_RUN"}\\n')
        marker.flush()
        os.fsync(marker.fileno())
    result = process(**job, **provider_ports)
    receipt = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "INCOMPLETE",
        "gateway_status": result.status,
        "next_action": result.next_action,
        "mode": result.mode,
        "source_url": job["source_url"],
        "source_sha256": result.source_sha256,
        "notion_id": result.notion_id,
        "cortex_id": result.cortex_id,
        "provider_identity_attested": False,
        "provider_readback_claimed_by_host": result.status == "READBACK_MATCHED",
        "audit_gate_promoted": False,
    }
    # Replace only our own reserved marker with a complete, still
    # non-attesting receipt. Any interruption leaves reconciliation evidence.
    payload = (json.dumps(receipt, sort_keys=True) + "\n").encode("utf-8")
    fd = os.open(target, os.O_WRONLY | os.O_TRUNC)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        # Preserve partial evidence for reconciliation, never silently retry.
        raise
    return receipt
