"""Offline tests: bridge must never mistake assertions for provider receipts."""
import os
import tempfile
import unittest

from nexus_sandbox.transcript_ingestion import TranscriptCoordinator
from nexus_sandbox.transcript_receipt_bridge import record_verified_notion_archive


class ReceiptBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.coordinator = TranscriptCoordinator(os.path.join(self.temp.name, "journal.db"))
        self.args = dict(video_id="kokDVXUGdes", raw_transcript="verbatim transcript",
                         source_page_id="page-1", observed_raw_transcript="verbatim transcript",
                         observed_page_id="page-1", readback_ref="fetch-1",
                         source_revision="revision-1", observed_revision="revision-1",
                         host_readback_authenticated=True)

    def tearDown(self):
        self.coordinator.close()
        self.temp.cleanup()

    def call(self, **changes):
        return record_verified_notion_archive(self.coordinator,
                    **dict(self.args, **changes))

    def test_valid_receipt_and_identical_retry(self):
        a = self.call()
        self.assertEqual(a.status, "RECORDED")
        self.assertEqual(self.coordinator.next_stage(a.source_key), "ANALYSIS_COMPLETED")
        self.assertEqual(self.call().status, "RECORDED")
        self.assertEqual(self.coordinator.receipt(a.source_key)["status"], "INCOMPLETE")

    def test_untrusted_and_mismatched_readback_fail_closed(self):
        for changes in (dict(host_readback_authenticated=False),
                        dict(observed_page_id="other"),
                        dict(observed_revision="old"),
                        dict(observed_raw_transcript="truncated"),
                        dict(readback_ref="")):
            with self.subTest(changes=changes):
                self.assertEqual(self.call(**changes).status, "BLOCKED")
        self.assertIsNone(self.coordinator.get("youtube:kokDVXUGdes", "NOTION_ARCHIVE_VERIFIED"))

    def test_conflicting_retry_cannot_replace_verified_receipt(self):
        first = self.call()
        with self.assertRaisesRegex(ValueError, "Conflicting verified evidence"):
            self.call(readback_ref="different-fetch")
        self.assertEqual(self.coordinator.get(first.source_key,
                         "NOTION_ARCHIVE_VERIFIED").evidence["readback"], "fetch-1")

    def test_restart_recovers_checkpoint(self):
        key = self.call().source_key
        self.coordinator.close()
        self.coordinator = TranscriptCoordinator(os.path.join(self.temp.name, "journal.db"))
        self.assertEqual(self.coordinator.next_stage(key), "ANALYSIS_COMPLETED")


if __name__ == "__main__":
    unittest.main()
