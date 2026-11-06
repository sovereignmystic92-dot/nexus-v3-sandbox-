import pytest

from nexus_sandbox.cortex_handoff_preflight import HandoffBlocked, preflight

BASE = dict(
    transaction_key="NXS-LIVE-TRANSCRIPT-RAXLnCNA4w8-20261029",
    source_url="https://app.notion.com/p/4088c067daa4813bb1f0e1f1993120fb",
    analysis_url="https://app.notion.com/p/4088c067daa481a5bb0bf62e5ea3339b",
    destination_confirmed=True,
    registry_complete=True,
    expected_owner="owner-1",
    modules=[],
)

def test_absent_is_not_write_authorization():
    assert preflight(**BASE).status == "ELIGIBLE_FOR_SEPARATE_AUTHORIZED_CREATE"

def test_existing_reconciles():
    module = {"id": "module-1", "owner": "owner-1", "content": BASE["transaction_key"]}
    result = preflight(**{**BASE, "modules": [module]})
    assert result.status == "RECONCILE_EXISTING_NO_CREATE"
    assert result.matched_module == "module-1"

@pytest.mark.parametrize("override", [
    {"destination_confirmed": False},
    {"registry_complete": False},
    {"expected_owner": ""},
    {"modules": [{"id": "x", "owner": "other", "content": BASE["source_url"]}]},
    {"modules": [{"id": "x", "owner": "owner-1", "content": BASE["source_url"]},
                 {"id": "y", "owner": "owner-1", "content": BASE["transaction_key"]}]},
    {"modules": [{"id": "x", "owner": "owner-1"}]},
])
def test_fail_closed(override):
    with pytest.raises(HandoffBlocked):
        preflight(**{**BASE, **override})
