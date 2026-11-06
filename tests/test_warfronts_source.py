import hashlib
import unittest

from nexus_sandbox.warfronts_source import (
    CaptionSegment, prepare_warfronts_source,
)


class WarFrontsSourceTests(unittest.TestCase):
    def setUp(self):
        self.args = dict(
            video_id="RAXLnCNA4w8",
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

    def test_invalid_video_id_is_blocked(self):
        self.args["video_id"] = "not-a-valid-id"
        with self.assertRaises(ValueError):
            prepare_warfronts_source(**self.args)


if __name__ == "__main__":
    unittest.main()
