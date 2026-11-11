"""Read-only CP05 diagnostic: never promotes unauthenticated observations."""
import hashlib
import json
from datetime import datetime, timezone
from nexus_sandbox.cp05_cortex_reader import read_cortex_fixture

NYC_MODULE_ID = "module_01m3cjdj38ezqss3g276hmbvd5"

def diagnose(client=None, *, module_id=NYC_MODULE_ID):
    receipt = {
        "schema": "nexus.cp05.diagnostic.v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "module_id": module_id,
        "operation": "read_only",
        "provider_writes": 0,
        "audit_pass": False,
    }
    if client is None:
        receipt.update(status="BLOCKED_NO_HOST_CLIENT",
                       reason="No supported authenticated Cortex machine client injected")
        return receipt
    try:
        record, metadata = read_cortex_fixture(module_id, client=client)
        serialized = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        receipt.update(status="READ_ATTESTED_BY_CLIENT",
                       version=record.get("version"),
                       content_sha256=hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
                       source_reference=record.get("source_reference"),
                       host_metadata=metadata)
    except Exception as exc:
        # Never serialize exception messages: SDKs may include credentials or URLs.
        receipt.update(status="READ_BLOCKED", failure_type=type(exc).__name__)
    return receipt

if __name__ == "__main__":
    print(json.dumps(diagnose(), sort_keys=True))
