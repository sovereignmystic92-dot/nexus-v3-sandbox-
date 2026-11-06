import hashlib
import unittest
from nexus_sandbox.warfronts_transcript_diff import compare_transcripts

class WarFrontsTranscriptDiffTests(unittest.TestCase):
    def args(self, **overrides):
        a=dict(original='Haiti  text\n',candidate='Haiti text\n',original_provenance='notion:page-1',candidate_provenance='podcastrex:episode-1')
        a.update(overrides)
        return a
    def test_exact_digest_and_whitespace_difference(self):
        r=compare_transcripts(**self.args())
        self.assertNotEqual(r.original_sha256,r.candidate_sha256)
        self.assertEqual(r.original_sha256,hashlib.sha256(b'Haiti  text\n').hexdigest())
        self.assertFalse(r.identical)
        self.assertEqual(r.changes,())
    def test_word_replacement(self):
        r=compare_transcripts(**self.args(candidate='Haiti changed\n'))
        self.assertEqual(r.changes[0][0],'replace')
    def test_identical_text(self):
        r=compare_transcripts(**self.args(candidate='Haiti  text\n'))
        self.assertTrue(r.identical)
        self.assertEqual(r.status,'REVIEW_REQUIRED_NOT_AUTHORIZED')
    def test_missing_source_rejected(self):
        with self.assertRaises(ValueError):compare_transcripts(**self.args(original=''))
    def test_same_provenance_rejected(self):
        with self.assertRaises(ValueError):compare_transcripts(**self.args(candidate_provenance='notion:page-1'))
    def test_utf16_surrogate(self):
        r=compare_transcripts(**self.args(original='🧭 Haiti',candidate='Haiti'))
        self.assertEqual(r.original_utf16_units,8)
