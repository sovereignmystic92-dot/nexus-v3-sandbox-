"""Offline mapping from a verified GitHub run to a Cortex test fixture."""
import json
from .cortex_adapter import MARKER, Write
from .github_cortex_event import normalize_run

def make_fixture(run, source, target_name, request_key):
    envelope = normalize_run(run)
    payload = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
    return Write(
        key=request_key,
        name=target_name,
        content=f"{MARKER}\n{request_key}\n{payload}",
        dependencies=(),
        source=source,
    )
