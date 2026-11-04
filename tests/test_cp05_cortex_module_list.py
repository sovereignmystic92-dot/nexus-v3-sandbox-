"""Offline contract tests for the Cortex module_list read-only fallback."""
import json
import pytest
from nexus_sandbox.cp05_cortex_module_list import observe_cortex_module_list

ID = "module_01m6kzebbfdk4ptbsg88gsf0ja"
NAME = "NEXUS CP05 SYNTHETIC CORTEX READBACK 2026-11-04 A"
MODULE = {"id": ID, "name": NAME, "version": 1, "content": "synthetic",
          "dependencies": [], "archived": False}


def invoke_with(data):
    def invoke(tool, args):
        assert tool == "module_list"
        assert args == {"q": NAME, "permission": "module.view", "limit": 100}
        return {"text": json.dumps(data)}
    return invoke


def read(data):
    return observe_cortex_module_list(
        module_id=ID, exact_name=NAME, invoke=invoke_with(data))


def test_exact_exhausted_result_is_observation_only():
    record, meta = read({"data": [MODULE], "has_more": False})
    assert record["module_id"] == ID
    assert record["version"] == 1
    assert meta == {"authenticated": False, "complete_inventory": False}


@pytest.mark.parametrize("data", [
    {"data": [MODULE], "has_more": True},
    {"data": [MODULE, MODULE], "has_more": False},
    {"data": [], "has_more": False},
    {"data": [dict(MODULE, id="module_other")], "has_more": False},
    {"data": [dict(MODULE, version=True)], "has_more": False},
    {"data": [dict(MODULE, archived=True)], "has_more": False},
    {"data": [dict(MODULE, dependencies="bad")], "has_more": False},
])
def test_unsafe_results_rejected(data):
    with pytest.raises(ValueError):
        read(data)


def test_empty_get_style_response_not_accepted():
    with pytest.raises(ValueError):
        observe_cortex_module_list(module_id=ID, exact_name=NAME, invoke=lambda *_: {})
