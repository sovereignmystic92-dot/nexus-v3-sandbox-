"""Source-bound read-only CSF intake tests; no external service."""
import hashlib
import unittest

from nexus_sandbox.csf_notional_intake import prepare_source_receipt
from nexus_sandbox.csf_v02 import CSFValidationError


def sample(text="Paragraph one.\n\nParagraph two."):
    return {
        "source_url": "https://app.notion.com/p/4088c067daa4813bb1f0e1f1993120fb",
        "source_revision": "2026-10-29T23:44:29.194Z",
        "document_id": "notion:4088c067-daa4-813b-b1f0-e1f1993120fb",
        "transcript": text,
        "expected_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


class TestNotionCSFReadOnlyIntake(unittest.TestCase):
    def test_source_bound_receipt(self):
        r = prepare_source_receipt(sample())
        self.assertEqual(r["status"], "READ_ONLY_SOURCE_PREPARED")
        self.assertEqual(r["segment_count"], 2)
        self.assertEqual(r["candidates"], [])
        self.assertFalse(r["provider_called"])
        self.assertEqual(r["external_writes"], 0)
        self.assertFalse(r["audit_gate_promoted"])

    def test_mismatched_hash_rejected(self):
        e = sample()
        e["transcript"] += " tampered"
        with self.assertRaises(CSFValidationError):
            prepare_source_receipt(e)

    def test_missing_revision_rejected(self):
        e = sample()
        e["source_revision"] = ""
        with self.assertRaises(CSFValidationError):
            prepare_source_receipt(e)

    def test_untrusted_source_rejected(self):
        e = sample()
        e["source_url"] = "https://example.com/fake"
        with self.assertRaises(CSFValidationError):
            prepare_source_receipt(e)

    def test_extra_fields_rejected(self):
        e = sample()
        e["authorize_cortex_write"] = True
        with self.assertRaises(CSFValidationError):
            prepare_source_receipt(e)


if __name__ == "__main__":
    unittest.main()
