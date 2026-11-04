"""Tests for the supervised ChatGPT-to-GitHub CP05 evidence boundary."""
import json
from pathlib import Path
from nexus_sandbox.cp05_chat_github_bridge import validate_chat_github_bridge

F = json.loads((Path(__file__).parent / "fixtures" /
                "cp05_connector_observation_20261104.json").read_text())
E = {
    "schema": "nexus.cp05.chat-github-bridge.v1",
    "execution_mode": "supervised_read_only",
    "checkpoint_status": "NOT_ATTESTED",
    "notion": {"page_id": F["notion"]["page_id"],
               "fixture_id": F["notion"]["fixture_id"],
               "payload": F["notion"]["expected_payload"]},
    "cortex": {"module_id": F["cortex"]["module_id"],
               "source_page_id": F["notion"]["page_id"],
               "payload": F["cortex"]["expected_payload"],
               "version": F["cortex"]["version"]},
}


def test_matching_bridge_is_not_host_attestation():
    result = validate_chat_github_bridge(F, E)
    assert result.status == "OBSERVATIONS_MATCH"
    assert result.reason == "REQUIRES_INDEPENDENT_HOST_ATTESTATION"


def test_claimed_checkpoint_completion_is_rejected():
    assert validate_chat_github_bridge(
        F, dict(E, checkpoint_status="COMPLETE")).status == "BLOCKED"


def test_mismatched_source_or_payload_rejected():
    for section, field in (("notion", "page_id"), ("notion", "payload"),
                           ("cortex", "source_page_id"), ("cortex", "module_id")):
        altered = dict(E, **{section: dict(E[section], **{field: "wrong"})})
        assert validate_chat_github_bridge(F, altered).status == "BLOCKED"


def test_automatic_mode_rejected():
    assert validate_chat_github_bridge(
        F, dict(E, execution_mode="automatic")).status == "BLOCKED"
