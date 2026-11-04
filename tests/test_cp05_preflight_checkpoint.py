"""CP05 preflight-to-checkpoint composition: blocked paths never touch journal."""
import json
from pathlib import Path
from unittest.mock import Mock, patch

from nexus_sandbox.cp05_preflight_checkpoint import record_preflight_bound_cortex_output


FIXTURE = json.loads((Path(__file__).parent / "fixtures" /
                      "cp05_connector_observation_20261104.json").read_text())
N = {"page_id": FIXTURE["notion"]["page_id"],
     "fixture_id": FIXTURE["notion"]["fixture_id"],
     "payload": FIXTURE["notion"]["expected_payload"]}
C = {"module_id": FIXTURE["cortex"]["module_id"],
     "source_page_id": N["page_id"],
     "payload": FIXTURE["cortex"]["expected_payload"],
     "version": FIXTURE["cortex"]["version"]}
FLAGS = dict(notion_authenticated=True, cortex_authenticated=True,
             notion_complete=True, cortex_complete=True)


def invoke(n=N, c=C, **flags):
    return record_preflight_bound_cortex_output(
        Mock(), fixture=FIXTURE, notion_observation=n, cortex_observation=c,
        expected_notion=Mock(), observed_notion=Mock(), **flags)


def test_no_trust_never_calls_checkpoint():
    with patch("nexus_sandbox.cp05_preflight_checkpoint.record_bound_cortex_output") as downstream:
        assert invoke().status == "BLOCKED"
        downstream.assert_not_called()


def test_tamper_never_calls_checkpoint():
    with patch("nexus_sandbox.cp05_preflight_checkpoint.record_bound_cortex_output") as downstream:
        assert invoke(c=dict(C, payload="tampered"), **FLAGS).status == "BLOCKED"
        downstream.assert_not_called()


def test_missing_cortex_readback_never_calls_checkpoint():
    with patch("nexus_sandbox.cp05_preflight_checkpoint.record_bound_cortex_output") as downstream:
        assert invoke(**FLAGS).next_action == "VERIFY_CORTEX_HOST_READBACK"
        downstream.assert_not_called()


def test_verified_preflight_delegates_but_does_not_complete_by_itself():
    with patch("nexus_sandbox.cp05_preflight_checkpoint.record_bound_cortex_output") as downstream:
        downstream.return_value = Mock(status="BLOCKED", next_action="VERIFY_NOTION_ARCHIVE_CHECKPOINT")
        result = invoke(**FLAGS, host_readback_authenticated=True,
                        output_inventory_complete=True)
        assert result.status == "BLOCKED"
        downstream.assert_called_once()
