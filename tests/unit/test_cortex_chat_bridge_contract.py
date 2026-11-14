import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from cortex_chat_bridge_contract import advance, make_handoff


class CortexChatBridgeTests(unittest.TestCase):
    def setUp(self):
        self.source = {"notion_page_id": "page-1", "source_revision": "rev-2", "sha256": "a" * 64}
        self.analysis = {"analysis_id": "csf-1", "revision": "v2",
                         "artifact_uri": "github-artifact:123", "sha256": "b" * 64}
        self.handoff = make_handoff(self.source, self.analysis)

    def test_deterministic_idempotency_and_no_network_claims(self):
        again = make_handoff(self.source, self.analysis)
        self.assertEqual(self.handoff["idempotency_key"], again["idempotency_key"])
        self.assertFalse(self.handoff["cortex_persisted"])
        self.assertEqual(self.handoff["state"], "PREPARED")

    def test_revision_changes_identity(self):
        changed = dict(self.analysis, revision="v3")
        self.assertNotEqual(self.handoff["idempotency_key"],
                            make_handoff(self.source, changed)["idempotency_key"])

    def test_requires_verified_readback_before_completion(self):
        ready = advance(self.handoff, "READY_FOR_CHAT")
        sent = advance(ready, "SUBMITTED", {"evidence_ref": "github:submitted"})
        with self.assertRaises(ValueError):
            advance(sent, "COMPLETE")
        with self.assertRaises(ValueError):
            advance(sent, "READBACK_VERIFIED", {"evidence_ref": "github:readback", "verified": False})
        evidence = {"evidence_ref": "github:readback", "verified": True,
                    "idempotency_key": self.handoff["idempotency_key"],
                    "cortex_record_id": "cortex-123",
                    "source_sha256": self.source["sha256"],
                    "analysis_sha256": self.analysis["sha256"]}
        verified = advance(sent, "READBACK_VERIFIED", evidence)
        self.assertTrue(verified["cortex_persisted"])
        self.assertFalse(sent["cortex_persisted"])
        self.assertEqual(advance(verified, "COMPLETE")["state"], "COMPLETE")

    def test_rejects_wrong_readback_checksum(self):
        sent = advance(advance(self.handoff, "READY_FOR_CHAT"), "SUBMITTED",
                       {"evidence_ref": "github:submitted"})
        with self.assertRaisesRegex(ValueError, "source checksum"):
            advance(sent, "READBACK_VERIFIED", {"evidence_ref": "github:readback",
                "verified": True, "idempotency_key": self.handoff["idempotency_key"],
                "cortex_record_id": "record", "source_sha256": "c" * 64,
                "analysis_sha256": self.analysis["sha256"]})

    def test_retry_requires_evidence_and_resubmission(self):
        sent = advance(advance(self.handoff, "READY_FOR_CHAT"), "SUBMITTED",
                       {"evidence_ref": "github:submitted"})
        with self.assertRaises(ValueError):
            advance(sent, "RETRY_REQUIRED")
        retry = advance(sent, "RETRY_REQUIRED", {"evidence_ref": "github:failure"})
        self.assertFalse(retry["cortex_persisted"])
        self.assertEqual(advance(retry, "READY_FOR_CHAT")["state"], "READY_FOR_CHAT")

    def test_rejects_missing_source_checksum(self):
        with self.assertRaises(ValueError):
            make_handoff(dict(self.source, sha256=""), self.analysis)


if __name__ == "__main__":
    unittest.main()
