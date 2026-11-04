"""Offline evidence-bound Cortex checkpoint tests."""
import os
import tempfile
import unittest

from nexus_sandbox.transcript_ingestion import TranscriptCoordinator, digest_source
from nexus_sandbox.cortex_checkpoint_bridge import record_verified_cortex_output


class CortexBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.journal = TranscriptCoordinator(os.path.join(self.temp.name, "state.db"))
        self.key = self.journal.receive("kokDVXUGdes", "raw source")
        self.digest = digest_source("raw source")
        self.route = dict(source_kind="TRANSCRIPT", source_store="NOTION",
                          source_id="page1", source_revision="rev1",
                          source_sha256=self.digest, output_kind="NEXUS_OUTPUT",
                          output_store="CORTEX", output_id="out1",
                          output_revision="rev1", output_source_id="page1",
                          output_source_sha256=self.digest)
        self.output = dict(output_id="out1", source_id="page1",
                           source_sha256=self.digest, revision="rev1",
                           analysis="bounded synthetic analysis")
        self.kwargs = dict(source_key=self.key, route=self.route,
                           expected_output=self.output, observed_output=self.output,
                           readback_ref="cortex-fetch-1",
                           host_readback_authenticated=True, source_verified=True,
                           authority_verified=True, output_inventory_complete=True)

    def tearDown(self):
        self.journal.close()
        self.temp.cleanup()

    def invoke(self, **changes):
        return record_verified_cortex_output(self.journal,
                   **dict(self.kwargs, **changes))

    def complete_prior(self):
        self.journal.record(self.key, "NOTION_ARCHIVE_VERIFIED", "COMPLETE",
                            {"destination": "notion:page1", "readback": "notion-fetch",
                             "source_revision": "rev1", "raw_sha256": self.digest},
                            independently_read_back=True)
        self.journal.record(self.key, "ANALYSIS_COMPLETED", "COMPLETE",
                            {"destination": "analysis:artifact1", "readback": "analysis-fetch"},
                            independently_read_back=True)

    def test_prior_checkpoints_required(self):
        self.assertEqual(self.invoke().next_action, "VERIFY_NOTION_ARCHIVE_CHECKPOINT")
        self.complete_prior()
        self.assertEqual(self.invoke().status, "RECORDED")
        self.assertEqual(self.journal.next_stage(self.key), "RECEIPT_RECORDED")
        self.assertEqual(self.invoke().status, "RECORDED")

    def test_mismatched_and_untrusted_readback_blocked(self):
        self.complete_prior()
        cases = [dict(host_readback_authenticated=False),
                 dict(output_inventory_complete=False),
                 dict(observed_output=dict(self.output, analysis="different")),
                 dict(route=dict(self.route, source_revision="stale")),
                 dict(readback_ref="")]
        for changes in cases:
            with self.subTest(changes=changes):
                self.assertEqual(self.invoke(**changes).status, "BLOCKED")
        self.assertIsNone(self.journal.get(self.key, "CORTEX_OUTPUT_VERIFIED"))

    def test_conflicting_verified_retry_rejected(self):
        self.complete_prior()
        self.assertEqual(self.invoke().status, "RECORDED")
        with self.assertRaisesRegex(ValueError, "Conflicting verified evidence"):
            self.invoke(readback_ref="other-fetch")

    def test_restart_recovery(self):
        self.complete_prior()
        self.invoke()
        self.journal.close()
        self.journal = TranscriptCoordinator(os.path.join(self.temp.name, "state.db"))
        self.assertEqual(self.journal.next_stage(self.key), "RECEIPT_RECORDED")


if __name__ == "__main__":
    unittest.main()
