import hashlib
import unittest
from nexus_sandbox.csf_source_intake import prepare_source
from nexus_sandbox.csf_v02 import CSFValidationError

TEXT = ("This is a hypothetical colony ship scenario with uncertain conclusions. " * 40)
DIGEST = hashlib.sha256(TEXT.encode("utf-8")).hexdigest()

class SourceIntakeTests(unittest.TestCase):
    def test_new_source_is_prepared_without_provider_or_writes(self):
        result = prepare_source(TEXT, document_id="isaac-arthur-local-001", expected_sha256=DIGEST)
        self.assertEqual(result["source_digest"], DIGEST)
        self.assertGreater(result["segment_count"], 1)
        self.assertGreater(result["review_item_count"], 0)
        self.assertFalse(result["provider_called"])
        self.assertEqual(result["external_writes"], 0)
        self.assertFalse(result["classification_performed"])

    def test_mutated_or_unpinned_source_rejected(self):
        for content, pin in [(TEXT + "changed", DIGEST), (TEXT, ""), (TEXT, "0" * 64)]:
            with self.subTest(pin=pin):
                with self.assertRaises(CSFValidationError):
                    prepare_source(content, document_id="local", expected_sha256=pin)

    def test_invalid_document_rejected(self):
        with self.assertRaises(CSFValidationError):
            prepare_source(TEXT, document_id="", expected_sha256=DIGEST)

if __name__ == "__main__":
    unittest.main()
