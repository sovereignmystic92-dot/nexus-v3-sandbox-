"""Observed Cortex connector module_list response contract (read-only).

The test replays the response shape observed on 2026-11-04, not a GitHub
Actions authenticated request. It never promotes connector access to host trust.
"""
import json
from nexus_sandbox.cp05_cortex_module_list import observe_cortex_module_list
from nexus_sandbox.cp05_cortex_reader import read_cortex_fixture
import pytest

NAME = "NEXUS CP05 SYNTHETIC CORTEX READBACK 2026-11-04 A"
ID = "module_01m6kzebbfdk4ptbsg88gsf0ja"
TEXT = (
    "SYNTHETIC TEST RECORD — NOT PRODUCTION KNOWLEDGE.\n"
    "Fixture ID: NEXUS-CP05-CORTEX-20261104-A\n"
    "Expected payload: The copper lantern stays lit at dawn.\n"
    "Source Notion fixture page ID: 40e8c067-daa4-8199-9f12-c9b6486de444\n"
    "Source Notion fixture label: NEXUS-CP05-NOTION-20261104-A\n"
    "Purpose: verify connector-side Cortex module creation, identity, exact content and subsequent independent retrieval. No claim of authenticated Nexus runtime, transactional Notion revision lock, deployed CP05 checkpoint enforcement, or audit gate closure. Do not promote as canonical Nexus Output."
)


def test_observed_connector_shape_and_content_still_unattested():
    response = {"text": json.dumps({
        "data": [{
            "id": ID, "name": NAME, "version": 1, "content": TEXT,
            "dependencies": [], "archived": False,
            "owner": "01a0b33e-deda-d7a5-dcf5-faeae65b486f",
        }], "has_more": False,
    })}
    calls = []
    def invoke(tool, args):
        calls.append((tool, args))
        return response
    record, meta = observe_cortex_module_list(
        module_id=ID, exact_name=NAME, invoke=invoke)
    assert record["content"] == TEXT
    assert record["version"] == 1
    assert record["dependencies"] == []
    assert calls == [("module_list", {
        "q": NAME, "permission": "module.view", "limit": 100})]
    assert meta == {"authenticated": False, "complete_inventory": False}

    class UnattestedClient:
        def read_module(self, module_id):
            return record, meta

    with pytest.raises(ValueError, match="authentication not attested"):
        read_cortex_fixture(ID, client=UnattestedClient())
