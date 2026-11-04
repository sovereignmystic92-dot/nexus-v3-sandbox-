"""Connector evidence must never be promoted into Cortex host authentication."""
import json
from pathlib import Path

RECEIPT = json.loads((Path(__file__).parent / "fixtures" /
                      "cp05_cortex_connector_read_receipt_20261104.json").read_text())


def test_cortex_connector_receipt_is_read_only_and_unattested():
    assert RECEIPT["schema"] == "nexus.cp05.cortex-connector-observation.v1"
    assert RECEIPT["scope"].startswith("connector-side-read-only")
    assert RECEIPT["observed"]["connector_search_found"] is True
    assert RECEIPT["observed"]["context_get_returned_empty_object"] is True
    assert RECEIPT["observed"]["writes"] == 0
    assert not any(RECEIPT["trust"].values())


def test_connector_receipt_binds_exact_synthetic_fixture():
    module = RECEIPT["module"]
    assert module["id"] == "module_01m6kzebbfdk4ptbsg88gsf0ja"
    assert module["version"] == 1
    assert module["source_notion_page_id"] == "40e8c067-daa4-8199-9f12-c9b6486de444"
    assert module["expected_payload"] == "The copper lantern stays lit at dawn."
