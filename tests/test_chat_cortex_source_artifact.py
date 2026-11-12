import unittest
from unittest.mock import patch
from nexus_sandbox.chat_cortex_source_artifact import build_receipt

META = {"source_id": "4168c067-daa4-8111-bda6-ef07325583ed",
        "source_revision": "revision-1", "truncated": False, "unknown_block_count": 0}
VERIFIED = {"notion_source_id": META["source_id"], "readback_sha256":
            "a74abe591255afcd03af59eb34d525e997486a0118542679b77edd766380c867",
            "pending_cortex_processing": True, "readback_verified": True,
            "source_revision": "revision-1", "byte_count": 37274, "chunk_count": 4}

class SourceArtifactTests(unittest.TestCase):
    def test_fail_closed_without_complete_metadata(self):
        with self.assertRaises(ValueError):
            build_receipt("", {}, destination_module="cortex", authorization_reference="issue-202",
                          github_run_id="1", github_run_attempt="1", github_sha="abc")
    @patch("nexus_sandbox.chat_cortex_source_artifact.prepare_source_ready")
    @patch("nexus_sandbox.chat_cortex_source_artifact.verify_notion_export")
    def test_receipt_has_provenance_and_no_execution_claim(self, verify, prepare):
        verify.return_value = VERIFIED
        prepare.return_value = {"state": "CHAT_REVIEW_REQUIRED", "packet": {"packet_id": "p"},
                                "triage": {"decision": "REVIEW_REQUIRED"}}
        result = build_receipt("export", META, destination_module="cortex",
                               authorization_reference="issue-202",
                               github_run_id="123", github_run_attempt="2", github_sha="abc")
        self.assertEqual(result["github_run_id"], "123")
        self.assertEqual(result["source_bytes"], 37274)
        self.assertTrue(result["source_ready_emitted"])
        self.assertFalse(result["chat_invoked"])
        self.assertFalse(result["cortex_called"])
        self.assertEqual(verify.call_args.kwargs["truncated"], False)
    @patch("nexus_sandbox.chat_cortex_source_artifact.verify_notion_export", side_effect=ValueError("bad source"))
    def test_bad_readback_never_prepares_packet(self, verify):
        with self.assertRaises(ValueError):
            build_receipt("bad", META, destination_module="cortex", authorization_reference="issue-202",
                          github_run_id="1", github_run_attempt="1", github_sha="abc")

if __name__ == "__main__":
    unittest.main()
