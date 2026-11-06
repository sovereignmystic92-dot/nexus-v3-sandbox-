import pytest

from nexus_sandbox.cortex_handoff_readback import ReadbackFailure, verify_readback

ARGS = dict(expected_id="module-1", expected_owner="owner-1",
            transaction_key="transaction-1",
            source_url="https://app.notion.com/p/source",
            analysis_url="https://app.notion.com/p/analysis",
            expected_analysis="derived analysis text")
BODY = "\\n".join((ARGS["transaction_key"], ARGS["source_url"],
                   ARGS["analysis_url"], ARGS["expected_analysis"]))
MODULE = dict(id="module-1", owner="owner-1", version=1,
              archived=False, content=BODY)

def test_complete_readback():
    assert verify_readback(module=MODULE, **ARGS).status == "VERIFIED_MANUAL_OR_CONNECTOR_READBACK_ONLY"

@pytest.mark.parametrize("changes", [
    {"id": "wrong"}, {"owner": "wrong"}, {"version": 0},
    {"version": True}, {"archived": True}, {"content": "incomplete"},
    {"content": None}
])
def test_fail_closed(changes):
    with pytest.raises(ReadbackFailure):
        verify_readback(module={**MODULE, **changes}, **ARGS)

def test_no_readback():
    with pytest.raises(ReadbackFailure):
        verify_readback(module=None, **ARGS)
