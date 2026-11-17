import unittest
from nexus_sandbox.chat_cortex_source_ready import prepare_source_ready, SOURCE_DIGEST, SOURCE_ID

EVIDENCE = {
    "notion_source_id": SOURCE_ID,
    "readback_sha256": SOURCE_DIGEST,
    "pending_cortex_processing": True,
    "readback_verified": True,
    "source_revision": "supplied-text-capture-v1",
    "destination_module": "Nexus transcript derived knowledge (review destination)",
    "authorization_reference": "owner routing decision in GitHub issue 202",
}

class SourceReadyTests(unittest.TestCase):
    def test_review_only_deterministic(self):
        first = prepare_source_ready(EVIDENCE)
        self.assertEqual(first, prepare_source_ready(dict(reversed(list(EVIDENCE.items())))))
        self.assertEqual(first["state"], "CHAT_REVIEW_REQUIRED")
        self.assertEqual(first["packet"]["request"]["scope"], "read-only")
        self.assertFalse(first["cortex_called"])
        self.assertFalse(first["cortex_write_authorized"])
        self.assertEqual(first["triage"]["decision"], "REVIEW_REQUIRED")

    def test_missing_verification_rejected(self):
        for key, value in (("readback_verified", False),
                           ("pending_cortex_processing", False),
                           ("readback_sha256", "0" * 64),
                           ("notion_source_id", "wrong")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                prepare_source_ready({**EVIDENCE, key: value})

    def test_missing_destination_or_authorization_rejected(self):
        for key in ("destination_module", "authorization_reference", "source_revision"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                prepare_source_ready({**EVIDENCE, key: ""})

    def test_unexpected_fields_rejected(self):
        with self.assertRaises(ValueError):
            prepare_source_ready({**EVIDENCE, "client_secret": "forbidden"})

if __name__ == "__main__":
    unittest.main()
