import json
from pathlib import Path

from nexus_sandbox.cp05_connector_preflight import check_connector_pair


FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "cp05_connector_observation_20261104.json").read_text()
)
N = {"page_id": FIXTURE["notion"]["page_id"],
     "fixture_id": FIXTURE["notion"]["fixture_id"],
     "payload": FIXTURE["notion"]["expected_payload"]}
C = {"module_id": FIXTURE["cortex"]["module_id"],
     "source_page_id": N["page_id"],
     "payload": FIXTURE["cortex"]["expected_payload"],
     "version": 1}
TRUST = dict(notion_authenticated=True, cortex_authenticated=True,
             notion_complete=True, cortex_complete=True)


def test_default_fail_closed():
    assert check_connector_pair(FIXTURE, N, C).reason == "HOST_EVIDENCE_REQUIRED"


def test_partial_trust_fails():
    for key in TRUST:
        flags = dict(TRUST)
        flags[key] = False
        assert check_connector_pair(FIXTURE, N, C, **flags).status == "BLOCKED"


def test_nonboolean_trust_fails():
    flags = dict(TRUST)
    flags["notion_authenticated"] = "true"
    assert check_connector_pair(FIXTURE, N, C, **flags).reason == "INVALID_HOST_ASSERTION"


def test_matching_observations_are_preflight_only():
    result = check_connector_pair(FIXTURE, N, C, **TRUST)
    assert result.status == "MATCHED"
    assert result.reason.startswith("PREFLIGHT_ONLY")


def test_identity_and_payload_tampering_blocked():
    for target, field in ((N, "page_id"), (N, "fixture_id"), (N, "payload"),
                          (C, "module_id"), (C, "source_page_id"), (C, "payload")):
        changed = dict(target, **{field: "tampered"})
        n, c = (changed, C) if target is N else (N, changed)
        assert check_connector_pair(FIXTURE, n, c, **TRUST).status == "BLOCKED"


def test_stale_version_blocked():
    assert check_connector_pair(FIXTURE, N, dict(C, version=2), **TRUST).reason == "RECONCILE_CORTEX_VERSION"
