"""Offline CP05 composition tests; synthetic host attestations only."""
import os
import tempfile
import unittest

from nexus_sandbox.transcript_ingestion import TranscriptCoordinator, digest_source
from nexus_sandbox.notion_snapshot_guard import snapshot
from nexus_sandbox.cp05_bound_checkpoint import record_bound_cortex_output

TIME = "2026-11-04T15:38:03.604Z"


class BoundCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = TranscriptCoordinator(os.path.join(self.tmp.name, "state.db"))
        self.key = self.db.receive("kokDVXUGdes", "raw source")
        self.rawsha = digest_source("raw source")
        self.notion = snapshot("page1", TIME, "complete Notion content")
        self.route = dict(source_kind="TRANSCRIPT", source_store="NOTION",
                          source_id="page1", source_revision=TIME,
                          source_sha256=self.rawsha, output_kind="NEXUS_OUTPUT",
                          output_store="CORTEX", output_id="out1",
                          output_revision="rev1", output_source_id="page1",
                          output_source_sha256=self.rawsha)
        self.output = dict(output_id="out1", source_id="page1",
                           source_sha256=self.rawsha, revision="rev1",
                           analysis="bounded synthetic analysis")
        self.db.record(self.key, "NOTION_ARCHIVE_VERIFIED", "COMPLETE",
                       {"destination": "notion:page1", "readback": "notion-fetch",
                        "source_revision": TIME, "raw_sha256": self.rawsha,
                        "page_content_sha256": self.notion.content_sha256},
                       independently_read_back=True)
        self.db.record(self.key, "ANALYSIS_COMPLETED", "COMPLETE",
                       {"destination": "analysis:artifact1", "readback": "analysis-fetch"},
                       independently_read_back=True)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def run_bridge(self, **overrides):
        args = dict(expected_notion=self.notion, observed_notion=self.notion,
                    notion_host_authenticated=True, notion_inventory_complete=True,
                    source_key=self.key, route=self.route, expected_output=self.output,
                    observed_output=self.output, readback_ref="cortex-fetch-1",
                    host_readback_authenticated=True, source_verified=True,
                    authority_verified=True, output_inventory_complete=True)
        args.update(overrides)
        return record_bound_cortex_output(self.db, **args)

    def test_valid_synthetic_chain(self):
        self.assertEqual(self.run_bridge().status, "RECORDED")
        self.assertEqual(self.db.next_stage(self.key), "RECEIPT_RECORDED")

    def test_changed_timestamp_blocks_without_checkpoint(self):
        changed = snapshot("page1", "2026-11-04T15:39:03.604Z", "complete Notion content")
        self.assertEqual(self.run_bridge(observed_notion=changed).next_action,
                         "BLOCKED_CHANGED_TIMESTAMP")
        self.assertIsNone(self.db.get(self.key, "CORTEX_OUTPUT_VERIFIED"))

    def test_changed_content_blocks_without_checkpoint(self):
        changed = snapshot("page1", TIME, "different Notion content")
        self.assertEqual(self.run_bridge(observed_notion=changed).next_action,
                         "BLOCKED_CHANGED_CONTENT")
        self.assertIsNone(self.db.get(self.key, "CORTEX_OUTPUT_VERIFIED"))

    def test_untrusted_or_incomplete_host_blocks(self):
        for field in ("notion_host_authenticated", "notion_inventory_complete"):
            with self.subTest(field=field):
                self.assertEqual(self.run_bridge(**{field: False}).status, "BLOCKED")
        self.assertIsNone(self.db.get(self.key, "CORTEX_OUTPUT_VERIFIED"))

    def test_route_revision_mismatch_blocks(self):
        self.assertEqual(self.run_bridge(route=dict(self.route, source_revision="stale")).next_action,
                         "RECONCILE_NOTION_ROUTE_REVISION")


if __name__ == "__main__":
    unittest.main()
