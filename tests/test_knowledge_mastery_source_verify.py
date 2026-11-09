import hashlib
import unittest
from tools.knowledge_mastery_source_verify import verify_source, MASS_RELAYS

class ArchiveSourceVerifierTests(unittest.TestCase):
    def test_missing_full_source_fails_closed(self):
        self.assertEqual(verify_source(b"")["reason"], "BYTE_COUNT_MISMATCH")

    def test_excerpt_cannot_substitute_for_archive(self):
        self.assertEqual(verify_source(b"The mass relays.")["status"], "BLOCKED")

    def test_wrong_bytes_of_exact_length_fail(self):
        data = b"x" * MASS_RELAYS["byte_count"]
        self.assertEqual(verify_source(data)["reason"], "SOURCE_HASH_MISMATCH")

    def test_invalid_utf8_fails(self):
        self.assertEqual(verify_source(b"\\xff")["reason"], "INVALID_UTF8")

    def test_type_validation(self):
        self.assertEqual(verify_source("text")["reason"], "INVALID_INPUT")

    def test_control_fixture_accepts_only_exact_source(self):
        data = b"alpha" + b"beta"
        manifest = dict(source_id="synthetic:test", byte_count=len(data),
                        sha256=hashlib.sha256(data).hexdigest(),
                        chunks=((5, hashlib.sha256(b"alpha").hexdigest()),
                                (4, hashlib.sha256(b"beta").hexdigest())))
        result = verify_source(data, manifest)
        self.assertEqual(result["status"], "SOURCE_BYTES_VERIFIED")
        self.assertFalse(result["mastery_promoted"])
        self.assertEqual(result["provider_writes"], 0)

    def test_control_fixture_detects_bad_chunk_digest(self):
        data = b"alpha"
        manifest = dict(source_id="synthetic:test", byte_count=5,
                        sha256=hashlib.sha256(data).hexdigest(),
                        chunks=((5, "0" * 64),))
        self.assertEqual(verify_source(data, manifest)["reason"], "CHUNK_HASH_MISMATCH")

if __name__ == "__main__":
    unittest.main()
