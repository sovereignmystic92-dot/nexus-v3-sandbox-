"""The archived CP05 GitHub receipt is evidence, never a runtime authority."""
import json
from pathlib import Path

from nexus_sandbox.cp05_connector_preflight import check_connector_pair

FIXTURES = Path(__file__).parent / "fixtures"
PAIR = json.loads((FIXTURES / "cp05_connector_observation_20261104.json").read_text())
RECEIPT = json.loads((FIXTURES / "cp05_notion_host_read_receipt_41918014644.json").read_text())


def test_host_receipt_matches_fixed_source_identity_without_granting_authority():
    assert RECEIPT["notion"]["page_id"] == PAIR["notion"]["page_id"]
    assert RECEIPT["notion"]["result"] == "MATCHED_READ_ONLY"
    assert RECEIPT["notion"]["writes"] == 0
    assert RECEIPT["notion"]["block_count"] == 7
    assert len(RECEIPT["notion"]["extracted_text_sha256"]) == 64
    assert RECEIPT["limitations"]["cortex_runtime_host_authenticated"] is False
    assert RECEIPT["limitations"]["notion_checkpoint_attested"] is False
    assert RECEIPT["limitations"]["cp05_closed"] is False


def test_checked_in_receipt_cannot_satisfy_fresh_host_assertions():
    notion = dict(page_id=PAIR["notion"]["page_id"],
                  fixture_id=PAIR["notion"]["fixture_id"],
                  payload=PAIR["notion"]["expected_payload"])
    cortex = dict(module_id=PAIR["cortex"]["module_id"],
                  source_page_id=notion["page_id"],
                  payload=PAIR["cortex"]["expected_payload"],
                  version=PAIR["cortex"]["version"])
    verdict = check_connector_pair(PAIR, notion, cortex)
    assert verdict.status == "BLOCKED"
    assert verdict.reason == "HOST_EVIDENCE_REQUIRED"


def test_receipt_revision_does_not_silently_replace_frozen_fixture_revision():
    assert RECEIPT["notion"]["last_edited_at"] != PAIR["notion"]["last_edited_at"]
