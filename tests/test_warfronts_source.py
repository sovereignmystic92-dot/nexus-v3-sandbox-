import hashlib
import unittest

from nexus_sandbox.warfronts_source import (
    CaptionSegment, prepare_warfronts_source,
)


class WarFrontsSourceTests(unittest.TestCase):
    def setUp(self):
        self.args = dict(
            video_id="RAXLnCNA4w8",
            expected_channel_id="UCabcdefghijklmnopqrstuv",
            observed_channel_id="UCabcdefghijklmnopqrstuv",
            segments=(CaptionSegment(0, 0, 500, "  Exact text.\n"),
                      CaptionSegment(1, 500, 600, "Next line.")),
            channel_verified=True,
            captions_complete=True,
            caption_provenance_verified=True,
        )

    def test_preserves_exact_text_and_digest(self):
        result = prepare_warfronts_source(**self.args)
        self.assertEqual(result.transcript_sha256,
                         hashlib.sha256(b"  Exact text.\nNext line.").hexdigest())
        self.assertEqual(result.segments[0], ("0:0:500", "  Exact text.\n"))
        self.assertEqual(result.status, "AWAITING_NOTION_ARCHIVE_READBACK")

    def test_unverified_channel_is_blocked(self):
        self.args["channel_verified"] = False
        with self.assertRaises(ValueError):
            prepare_warfronts_source(**self.args)

    def test_incomplete_captions_are_blocked(self):
        self.args["captions_complete"] = False
        with self.assertRaises(ValueError):
            prepare_warfronts_source(**self.args)

    def test_unproven_caption_source_is_blocked(self):
        self.args["caption_provenance_verified"] = False
        with self.assertRaises(ValueError):
            prepare_warfronts_source(**self.args)

    def test_bad_sequence_is_blocked(self):
        self.args["segments"] = (CaptionSegment(1, 0, 500, "text"),)
        with self.assertRaises(ValueError):
            prepare_warfronts_source(**self.args)

    def test_mismatched_channel_id_is_blocked(self):
        self.args["observed_channel_id"] = "UCzyxwvutsrqponmlkjihgfe"
        with self.assertRaises(ValueError):
            prepare_warfronts_source(**self.args)

    def test_missing_channel_id_is_blocked(self):
        self.args["observed_channel_id"] = ""
        with self.assertRaises(ValueError):
            prepare_warfronts_source(**self.args)

    def test_invalid_video_id_is_blocked(self):
        self.args["video_id"] = "not-a-valid-id"
        with self.assertRaises(ValueError):
            prepare_warfronts_source(**self.args)


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



from nexus_sandbox.warfronts_snapshot_bridge import bind_warfronts_snapshot
from nexus_sandbox.transcript_completion import source_digest


class WarFrontsSnapshotBridgeTests(unittest.TestCase):
    def setUp(self):
        self.plan = prepare_warfronts_source(
            video_id="RAXLnCNA4w8",
            expected_channel_id="UCabcdefghijklmnopqrstuv",
            observed_channel_id="UCabcdefghijklmnopqrstuv",
            segments=(CaptionSegment(0, 0, 500, " Exact\\n"), CaptionSegment(1, 500, 500, "text")),
            channel_verified=True, captions_complete=True, caption_provenance_verified=True)
        self.args = dict(
            plan=self.plan, page_id="notion-source-1", parent_id="notion-parent-1",
            archive_video_id=self.plan.video_id, archive_channel_id=self.plan.channel_id,
            archive_text=" Exact\\ntext", archive_source_url=self.plan.source_url,
            archive_revision="revision-1", archive_complete=True, independent_readback=True)

    def test_exact_snapshot_digest(self):
        result = bind_warfronts_snapshot(**self.args)
        self.assertEqual(source_digest(result.source), self.plan.transcript_sha256)
        self.assertEqual(result.provider_writes, 0)
        self.assertEqual(result.status, "SOURCE_SNAPSHOT_READY_NOT_AUTHORIZED")

    def test_unverified_readback_holds(self):
        self.args["independent_readback"] = False
        with self.assertRaises(ValueError):
            bind_warfronts_snapshot(**self.args)

    def test_wrong_archive_text_holds(self):
        self.args["archive_text"] += " "
        with self.assertRaises(ValueError):
            bind_warfronts_snapshot(**self.args)

    def test_missing_page_holds(self):
        self.args["page_id"] = ""
        with self.assertRaises(ValueError):
            bind_warfronts_snapshot(**self.args)

    def test_same_parent_and_page_holds(self):
        self.args["parent_id"] = self.args["page_id"]
        with self.assertRaises(ValueError):
            bind_warfronts_snapshot(**self.args)

from test_warfronts_transcript_diff import WarFrontsTranscriptDiffTests

from test_warfronts_source_transfer import WarFrontsSourceTransferTests

if __name__ == "__main__":
    unittest.main()
