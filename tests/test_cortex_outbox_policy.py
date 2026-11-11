import unittest
from nexus_sandbox.cortex_outbox_policy import validate_manifest, authorize_commit, ProposalRejected

H = "a" * 64
def fixture():
    return dict(schema_version=1, source_system="synthetic", source_id_hash=H,
                source_digest=H, operation="create", target_key_hash=H,
                request_id="synthetic-001", status="PREPARED", evidence_refs=[],
                created_at="2026-11-08T00:00:00Z")

class OutboxTests(unittest.TestCase):
    def test_valid_proposal_is_not_commit(self):
        self.assertEqual(validate_manifest(fixture()).status, "PREPARED")
    def test_unexpected_content_field_rejected(self):
        x=fixture();x["transcript_text"]="private"
        with self.assertRaises(ProposalRejected): validate_manifest(x)
    def test_delete_rejected(self):
        x=fixture();x["operation"]="delete"
        with self.assertRaises(ProposalRejected): validate_manifest(x)
    def test_forged_committed_status_rejected(self):
        x=fixture();x["status"]="COMMITTED"
        with self.assertRaises(ProposalRejected): validate_manifest(x)
    def test_invalid_digest_rejected(self):
        x=fixture();x["source_digest"]="not-a-hash"
        with self.assertRaises(ProposalRejected): validate_manifest(x)
    def test_default_commit_blocked(self):
        self.assertEqual(authorize_commit().status, "BLOCKED")
    def test_grants_without_fencing_blocked(self):
        self.assertEqual(authorize_commit(identity_verified=True,grants_verified=True,approved_scope=True).status,"BLOCKED")
    def test_fencing_without_grants_blocked(self):
        self.assertEqual(authorize_commit(remote_fencing_verified=True).status,"BLOCKED")
    def test_all_conditions_only_eligible_for_review(self):
        self.assertEqual(authorize_commit(identity_verified=True,grants_verified=True,approved_scope=True,remote_fencing_verified=True).status,"ELIGIBLE_FOR_SEPARATE_REVIEW")

if __name__=="__main__":
    unittest.main()
