import pytest
from nexus_sandbox.cortex_handoff_orchestrator import execute_handoff, HandoffUncertain
from nexus_sandbox.cortex_handoff_preflight import HandoffBlocked

ARGS = dict(transaction_key="tx-1", source_url="https://app.notion.com/p/source",
            analysis_url="https://app.notion.com/p/analysis",
            analysis_text="bounded derived report", expected_owner="owner-1",
            destination_confirmed=True, registry_complete=True,
            modules=[], authorized_write=True)
CONTENT = "Transaction: tx-1\\nCanonical source: " + ARGS["source_url"] + "\\nCanonical analysis: " + ARGS["analysis_url"] + "\\nDerived analysis:\\n" + ARGS["analysis_text"]

def test_create_and_independent_readback():
    calls = []
    def create(name, content):
        calls.append(("create", name))
        assert content == CONTENT
        return {"id": "m-1"}
    def fetch(mid):
        calls.append(("fetch", mid))
        return dict(id="m-1", owner="owner-1", version=1, archived=False, content=CONTENT)
    result = execute_handoff(**ARGS, create_module=create, fetch_module=fetch)
    assert result.status == "CREATED_AND_READBACK_VERIFIED_NOT_LIVE_ACCEPTANCE"
    assert [c[0] for c in calls] == ["create", "fetch"]

def test_existing_never_creates():
    def forbidden(*_):
        raise AssertionError("must not create")
    module = dict(id="m-1", owner="owner-1", version=1, archived=False, content=CONTENT)
    result = execute_handoff(**{**ARGS, "modules": [module], "authorized_write": False},
                             create_module=forbidden, fetch_module=lambda _: module)
    assert result.status == "RECONCILED_EXISTING_NO_WRITE"

def test_no_authorization_no_write():
    with pytest.raises(HandoffBlocked):
        execute_handoff(**{**ARGS, "authorized_write": False},
                        create_module=lambda *_: (_ for _ in ()).throw(AssertionError()),
                        fetch_module=lambda _: None)

def test_ambiguous_create_does_not_retry():
    count = []
    def create(*_):
        count.append(1)
        raise TimeoutError("outcome unknown")
    with pytest.raises(HandoffUncertain):
        execute_handoff(**ARGS, create_module=create, fetch_module=lambda _: None)
    assert len(count) == 1

def test_bad_readback_uncertain():
    with pytest.raises(HandoffUncertain):
        execute_handoff(**ARGS, create_module=lambda *_: {"id": "m-1"},
                        fetch_module=lambda _: {"id": "m-1", "content": CONTENT})
