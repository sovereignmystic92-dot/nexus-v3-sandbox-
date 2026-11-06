import unittest
from nexus_sandbox.warfronts_source import CaptionSegment, prepare_warfronts_source
from nexus_sandbox.warfronts_archive_handoff import verify_archive_handoff


class WarFrontsArchiveHandoffTests(unittest.TestCase):
    def setUp(self):
        self.plan = prepare_warfronts_source(
            video_id="RAXLnCNA4w8",
            expected_channel_id="UCabcdefghijklmnopqrstuv",
            observed_channel_id="UCabcdefghijklmnopqrstuv",
            segments=(CaptionSegment(0, 0, 500, " Exact\\n"), CaptionSegment(1, 500, 500, "text")),
            channel_verified=True, captions_complete=True, caption_provenance_verified=True)
        self.args = dict(plan=self.plan, archive_video_id=self.plan.video_id,
                         archive_channel_id=self.plan.channel_id,
                         archive_text=" Exact\\ntext", archive_source_url=self.plan.source_url,
                         archive_revision="notion-revision-1", archive_complete=True,
                         independent_readback=True)

    def test_matching_readback_is_not_authorization(self):
        result = verify_archive_handoff(**self.args)
        self.assertEqual(result.status, "READBACK_MATCHED_NOT_AUTHORIZED")
        self.assertEqual(result.provider_writes, 0)

    def test_missing_independent_readback_blocks(self):
        self.args["independent_readback"] = False
        self.assertEqual(verify_archive_handoff(**self.args).status, "BLOCKED")

    def test_incomplete_archive_blocks(self):
        self.args["archive_complete"] = False
        self.assertEqual(verify_archive_handoff(**self.args).status, "BLOCKED")

    def test_changed_text_blocks(self):
        self.args["archive_text"] += " "
        self.assertEqual(verify_archive_handoff(**self.args).next_action, "RECONCILE_ARCHIVE_TEXT")

    def test_wrong_video_blocks(self):
        self.args["archive_video_id"] = "kokDVXUGdes"
        self.assertEqual(verify_archive_handoff(**self.args).status, "BLOCKED")

    def test_wrong_channel_blocks(self):
        self.args["archive_channel_id"] = "UCzyxwvutsrqponmlkjihgfe"
        self.assertEqual(verify_archive_handoff(**self.args).status, "BLOCKED")

    def test_missing_revision_blocks(self):
        self.args["archive_revision"] = ""
        self.assertEqual(verify_archive_handoff(**self.args).status, "BLOCKED")

    def test_false_positive_assertion_blocks(self):
        self.args["independent_readback"] = 1
        self.assertEqual(verify_archive_handoff(**self.args).status, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
