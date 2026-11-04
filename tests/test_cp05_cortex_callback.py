"""Synthetic callback bridge tests; never contact the live provider."""
import json
import pytest
from nexus_sandbox.cp05_cortex_callback import observe_cortex_module
from nexus_sandbox.cp05_cortex_reader import read_cortex_fixture

ID = "module_01m6kzebbfdk4ptbsg88gsf0ja"
NAME = "NEXUS CP05 SYNTHETIC CORTEX READBACK 2026-11-04 A"


def callback(tool, args):
    assert tool == "context_get"
    assert args == {"name": NAME}
    return {"structuredContent": {
        "id": ID, "name": NAME, "version": 1,
        "content": "synthetic only", "dependencies": [], "archived": False,
    }}


def test_callback_observation_does_not_self_attest():
    record, metadata = observe_cortex_module(
        module_id=ID, exact_name=NAME, invoke=callback)
    assert record["module_id"] == ID
    assert metadata == {"authenticated": False, "complete_inventory": False}
    class Client:
        def read_module(self, module_id):
            return record, metadata
    with pytest.raises(ValueError, match="authentication not attested"):
        read_cortex_fixture(ID, client=Client())


def test_wrong_identity_fails_closed():
    with pytest.raises(ValueError, match="identity mismatch"):
        observe_cortex_module(
            module_id="module_other", exact_name=NAME, invoke=callback)


def test_empty_or_malformed_callback_fails_closed():
    with pytest.raises(Exception):
        observe_cortex_module(module_id=ID, exact_name=NAME, invoke=lambda *_: {})
    with pytest.raises(ValueError):
        observe_cortex_module(module_id=ID, exact_name=NAME, invoke=None)
