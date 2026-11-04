import json
from pathlib import Path
from unittest.mock import Mock

from nexus_sandbox.cp05_read_only_probe import probe_cp05_read_only

F = json.loads((Path(__file__).parent / "fixtures" /
                "cp05_connector_observation_20261104.json").read_text())
N = {"page_id": F["notion"]["page_id"], "fixture_id": F["notion"]["fixture_id"],
     "payload": F["notion"]["expected_payload"]}
C = {"module_id": F["cortex"]["module_id"],
     "source_page_id": F["notion"]["page_id"],
     "payload": F["cortex"]["expected_payload"],
     "version": F["cortex"]["version"]}
ENV = {"NEXUS_NOTION_TOKEN": "placeholder", "NEXUS_CORTEX_TOKEN": "placeholder"}
CAPS = {k: True for k in (
    "notion_authenticated_full_page_read", "notion_complete_pagination",
    "cortex_authenticated_module_read", "cortex_complete_output_read",
    "independent_provider_readback")}
META = {"authenticated": True, "complete_inventory": True}


def run(n=None, c=None, env=ENV, caps=CAPS):
    nr = Mock(return_value=(N if n is None else n, META))
    cr = Mock(return_value=(C if c is None else c, META))
    result = probe_cp05_read_only(fixture=F, notion_reader=nr,
                                  cortex_reader=cr, environ=env,
                                  capabilities=caps)
    return result, nr, cr


def test_missing_credentials_never_calls_providers():
    result, nr, cr = run(env={})
    assert result.status == "BLOCKED"
    nr.assert_not_called()
    cr.assert_not_called()


def test_matching_read_only_does_not_authorize_checkpoint():
    result, nr, cr = run()
    assert result.status == "READ_ONLY_MATCH"
    assert result.reason == "NO_CHECKPOINT_WRITE_AUTHORIZED"
    nr.assert_called_once_with(F["notion"]["page_id"])
    cr.assert_called_once_with(F["cortex"]["module_id"])


def test_tampered_cortex_fails_closed():
    result, _, _ = run(c=dict(C, payload="changed"))
    assert result.status == "BLOCKED"


def test_unverified_authentication_fails_closed():
    nr = Mock(return_value=(N, dict(META, authenticated=False)))
    cr = Mock(return_value=(C, META))
    result = probe_cp05_read_only(fixture=F, notion_reader=nr,
                                  cortex_reader=cr, environ=ENV,
                                  capabilities=CAPS)
    assert result.status == "BLOCKED"


def test_provider_error_never_leaks_exception():
    nr = Mock(side_effect=RuntimeError("sensitive provider error"))
    result = probe_cp05_read_only(fixture=F, notion_reader=nr,
                                  cortex_reader=Mock(), environ=ENV,
                                  capabilities=CAPS)
    assert result.reason == "PROVIDER_READ_FAILED"
    assert "sensitive" not in repr(result)
