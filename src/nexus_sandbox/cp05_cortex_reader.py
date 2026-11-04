"""CP05 Cortex read-only adapter for an authenticated provider client.

Socra Cortex's connected ChatGPT tools do not establish a public REST
endpoint or a GitHub Actions token contract. This adapter deliberately
requires an injected client instead of guessing URLs or authentication.
"""
from collections.abc import Mapping


def read_cortex_fixture(module_id, *, client):
    """Read an exact module by ID using an authenticated, read-only host client.

    Client contract: read_module(module_id) -> (module_mapping, metadata_mapping).
    Metadata must be independently supplied by the host from provider access,
    not from the fixture. Never infer identity or grants from a matching payload.
    """
    if not isinstance(module_id, str) or not module_id.startswith("module_"):
        raise ValueError("Invalid Cortex module identifier")
    if client is None or not callable(getattr(client, "read_module", None)):
        raise ValueError("Authenticated Cortex reader required")
    result = client.read_module(module_id)
    if not isinstance(result, tuple) or len(result) != 2:
        raise ValueError("Invalid Cortex reader response")
    record, metadata = result
    if not isinstance(record, Mapping) or not isinstance(metadata, Mapping):
        raise ValueError("Invalid Cortex record")
    if record.get("module_id") != module_id:
        raise ValueError("Cortex module identity mismatch")
    if metadata.get("authenticated") is not True:
        raise ValueError("Cortex authentication not attested")
    if metadata.get("complete_inventory") is not True:
        raise ValueError("Cortex content inventory incomplete")
    return dict(record), {
        "authenticated": True,
        "complete_inventory": True,
    }
