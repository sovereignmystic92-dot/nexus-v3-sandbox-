"""Safety tests for opt-in CP05 preflight-to-checkpoint entrypoint."""
import json
from pathlib import Path

from nexus_sandbox.cp05_preflight_bound_bridge import record_preflight_bound_output
from nexus_sandbox.notion_snapshot_guard import snapshot

F = json.loads((Path(__file__).parent / "fixtures" /
                "cp05_connector_observation_20261104.json").read_text())
N = dict(page_id=F["notion"]["page_id"], fixture_id=F["notion"]["fixture_id"],
         payload=F["notion"]["expected_payload"])
C = dict(module_id=F["cortex"]["module_id"], source_page_id=N["page_id"],
         payload=F["cortex"]["expected_payload"], version=1)
S = snapshot(N["page_id"], F["notion"]["last_edited_at"], N["payload"])


class MustNotCallCoordinator:
    def get(self, *args, **kwargs):
        raise AssertionError("Coordinator must not be reached before preflight")


def run(**kwargs):
    args = dict(fixture=F, notion_observation=N, cortex_observation=C,
                expected_notion=S, observed_notion=S, source_key="synthetic")
    args.update(kwargs)
    return record_preflight_bound_output(MustNotCallCoordinator(), **args)


def test_default_host_missing_blocks_before_checkpoint():
    assert run().next_action == "HOST_EVIDENCE_REQUIRED"


def test_mismatched_cortex_record_blocks_even_with_flags():
    assert run(cortex_observation=dict(C, payload="changed"),
               notion_authenticated=True, cortex_authenticated=True,
               notion_complete=True, cortex_complete=True).next_action == (
                   "RECONCILE_PROVIDER_OBSERVATIONS")


def test_no_override_of_host_flags():
    assert run(notion_authenticated=True, cortex_authenticated=True,
               notion_complete=True, cortex_complete=True,
               source_verified=True).next_action == "DUPLICATE_HOST_ASSERTIONS"
