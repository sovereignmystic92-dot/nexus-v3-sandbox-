"""Check checked-in CP05 connector observations against the fixture."""
import json
from pathlib import Path
from nexus_sandbox.cp05_bridge_evidence import verify_persisted_bridge_evidence

ROOT = Path(__file__).parent / "fixtures"
FIXTURE = json.loads((ROOT / "cp05_connector_observation_20261104.json").read_text())
EVIDENCE = json.loads((ROOT / "cp05_chat_github_observation_20261104.json").read_text())


def test_checked_in_evidence_matches_but_does_not_attest_runtime():
    result = verify_persisted_bridge_evidence(FIXTURE, EVIDENCE)
    assert result.status == "OBSERVATIONS_MATCH"
    assert result.reason == "RUNTIME_ATTESTATION_AND_CHECKPOINTS_REQUIRED"


def test_changed_notion_provenance_rejected():
    evidence = dict(EVIDENCE, sources=dict(EVIDENCE["sources"], notion_page="wrong"))
    assert verify_persisted_bridge_evidence(FIXTURE, evidence).status == "BLOCKED"


def test_changed_cortex_provenance_rejected():
    evidence = dict(EVIDENCE, sources=dict(EVIDENCE["sources"], cortex_module_id="wrong"))
    assert verify_persisted_bridge_evidence(FIXTURE, evidence).status == "BLOCKED"


def test_false_runtime_attestation_rejected():
    evidence = dict(EVIDENCE, evidence_scope="authenticated runtime verified")
    assert verify_persisted_bridge_evidence(FIXTURE, evidence).status == "BLOCKED"
